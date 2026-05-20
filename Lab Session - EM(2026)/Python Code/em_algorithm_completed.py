# -*- coding: utf-8 -*-
"""Completed EM Algorithm lab runner.

This file completes the lab notebook's main procedure and runs the EM yield
rate estimation for both the simplified and real-world datasets.
"""

import time

import numpy as np
import pandas as pd
import scipy.optimize

import custom_utility as cu


MAX_EMA_ITERATIONS = 100
EPSILON = 1.0e-99

OLD_COLUMNS = {
    "lot name": "Lot",
    "process prefix": "Process",
    "process suffix": "_MachineNo",
    "lot step": "Final",
    "processed": "CurrentTotalNum",
    "bad pieces": "BadNum",
    "total lot pieces": "TotalNum",
}
NEW_COLUMNS = {
    "lot name": "lot_name",
    "process prefix": "lot_machine_step",
    "lot step": "lot_step",
    "processed": "processed",
    "bad pieces": "bad_pieces",
}


def read_csv_files(filename):
    raw_csv = pd.read_csv(filename, encoding="big5", iterator=True, chunksize=10000)
    raw_csv = pd.concat(raw_csv, ignore_index=True)

    if OLD_COLUMNS["lot name"] in raw_csv.columns:
        col_1 = len(set(raw_csv.CurrentTotalNum))
        col_2 = len(set(raw_csv.TotalNum))
        process_col = "CurrentTotalNum"
        if col_1 < col_2:
            process_col = "TotalNum"

        raw_csv.rename(
            columns={
                OLD_COLUMNS["lot name"]: NEW_COLUMNS["lot name"],
                OLD_COLUMNS["lot step"]: NEW_COLUMNS["lot step"],
                process_col: NEW_COLUMNS["processed"],
                OLD_COLUMNS["bad pieces"]: NEW_COLUMNS["bad pieces"],
            },
            inplace=True,
        )

        raw_csv.columns = [
            col.replace(OLD_COLUMNS["process suffix"], "") for col in raw_csv.columns
        ]
        raw_csv.columns = [
            col.replace(OLD_COLUMNS["process prefix"], NEW_COLUMNS["process prefix"])
            for col in raw_csv.columns
        ]

    raw_csv["all_bad_pieces"] = raw_csv.bad_pieces
    raw_csv.loc[raw_csv["lot_step"] != -1, "all_bad_pieces"] = (
        raw_csv.processed - raw_csv.processed.shift(-1)
    )
    return raw_csv


def get_onehot_machine(source_data):
    machine_step_data = source_data.loc[
        :, source_data.columns.str.startswith("lot_machine_step")
    ]

    onehot_machine_step = (
        pd.get_dummies(machine_step_data, prefix="", prefix_sep="")
        .astype(np.int8)
        .T.groupby(level=0)
        .max()
        .T
    )

    last_step_index = source_data.lot_step[source_data.lot_step == -1].index.tolist()
    onehot_last_step = onehot_machine_step.iloc[last_step_index]
    machine_name = pd.DataFrame({"machine_name": list(onehot_last_step)})

    lot_step_machines = machine_step_data.copy()
    lot_step_machines = lot_step_machines.stack()
    lot_step_machines = lot_step_machines.groupby(level=0)
    lot_step_machines = lot_step_machines.apply(list)
    lot_step_machines = tuple(lot_step_machines)

    source_data["lot_step_machines"] = lot_step_machines
    return onehot_last_step, machine_name, source_data


def get_lot_information(source_data):
    def safe_division(x, y):
        if x == 0 or y == 0:
            return EPSILON
        return x / y

    columns = [
        "lot_name",
        "machine_used",
        "lot_total_pieces",
        "lot_good_pieces",
        "lot_bad_pieces",
        "lot_yield_rate",
        "ln_lot_yield_rate",
    ]
    lot_info = pd.DataFrame(data=None, columns=columns)
    lot_group = source_data.groupby("lot_name")

    for lot_name, lot_data in lot_group:
        last_step = lot_data.loc[lot_data.lot_step == -1]
        lot_all_defect = lot_data.all_bad_pieces.sum()
        lot_all_microcrack = lot_data.bad_pieces.sum()
        lot_badpieces_delta = lot_all_defect - lot_all_microcrack

        machine_used = last_step.lot_step_machines.iat[0]
        lot_total_pieces = lot_data.processed.max() - lot_badpieces_delta
        lot_good_pieces = last_step.processed.iat[0] - last_step.bad_pieces.iat[0]
        lot_bad_pieces = lot_total_pieces - lot_good_pieces
        lot_yield_rate = safe_division(lot_good_pieces, lot_total_pieces)
        ln_lot_yield_rate = np.log(lot_yield_rate)

        current_lot_info = [
            lot_name,
            machine_used,
            lot_total_pieces,
            lot_good_pieces,
            lot_bad_pieces,
            lot_yield_rate,
            ln_lot_yield_rate,
        ]
        lot_info.loc[len(lot_info)] = current_lot_info

    return lot_info


def get_machine_information(onehot_lot_data, machine_info, lot_info):
    machine_info["good_produced"] = 0
    machine_info = dict(zip(machine_info.machine_name, machine_info.good_produced))

    for _, lot_step in lot_info.iterrows():
        machine_used = lot_step.machine_used
        good_pieces = lot_step.lot_good_pieces
        for machine in machine_used:
            machine_info[machine] += good_pieces

    machine_info = pd.DataFrame(
        list(machine_info.items()), columns=["machine_name", "good_produced"]
    )
    machine_info["init_yieldrate"] = init_yieldrate_est(onehot_lot_data, lot_info)
    return machine_info


def init_yieldrate_est(onehot_data, lot_info):
    max_machine_step = len(onehot_data.columns)
    log_est_yieldrate = np.zeros((max_machine_step,))

    onehot_data = onehot_data.values
    lot_info = lot_info["ln_lot_yield_rate"].values
    lot_yieldrate = lot_info.reshape(-1, 1)

    config_dot_config = onehot_data.T.dot(onehot_data)
    config_dot_yield = onehot_data.T.dot(lot_yieldrate)

    def perform_least_square(params, cfg, i_yr, c_dot_c, c_dot_y):
        yieldrate = (c_dot_c.dot(params.reshape(-1, 1)) - c_dot_y) / 2
        val = cfg.dot(params.reshape(-1, 1)) - i_yr
        val *= val
        return val.sum() / 2, yieldrate

    log_est_yieldrate = scipy.optimize.fmin_l_bfgs_b(
        perform_least_square,
        log_est_yieldrate,
        None,
        (onehot_data, lot_yieldrate, config_dot_config, config_dot_yield),
        False,
        [(None, 0) for _ in range(max_machine_step)],
    )

    est_yieldrate = np.exp(log_est_yieldrate[0])
    return est_yieldrate


def e_step(source_data, machine_info):
    machine_info["exp_num_bad_pieces"] = 0
    machine_info["exp_pieces_going_bad"] = 0
    dict_exp_bad = dict(zip(machine_info.machine_name, machine_info.exp_num_bad_pieces))
    dict_going_bad = dict(
        zip(machine_info.machine_name, machine_info.exp_pieces_going_bad)
    )

    cur_yieldrate = dict(zip(machine_info.machine_name, machine_info.em_yieldrate))
    cur_log_yieldrate = dict(zip(machine_info.machine_name, machine_info.ln_yieldrate))

    for _, lot_step in source_data.iterrows():
        obs_bad_pieces = lot_step.bad_pieces

        if obs_bad_pieces > 0:
            lot_step_machines = lot_step.lot_step_machines
            exp_bad_pieces = []

            for step_number, machine in enumerate(lot_step_machines):
                bad_estimation_b1 = 1 - cur_yieldrate[machine]
                bad_estimation_b2 = 0
                previous_machines = lot_step_machines[0:step_number]
                for previous_machine in previous_machines:
                    bad_estimation_b2 += cur_log_yieldrate[previous_machine]

                bad_estimation_b2 = np.exp(bad_estimation_b2)
                bad_estimation = bad_estimation_b1 * bad_estimation_b2 + EPSILON
                exp_bad_pieces.append(bad_estimation)

            exp_percent_bad_pieces = exp_bad_pieces / sum(exp_bad_pieces)
            exp_num_bad_pieces = obs_bad_pieces * exp_percent_bad_pieces
            exp_pieces_going_bad = np.zeros((len(exp_num_bad_pieces),))

            for step_number, exp_bad_piece in reversed(
                list(enumerate(exp_num_bad_pieces))
            ):
                if step_number > 0:
                    exp_pieces_going_bad[step_number - 1] = (
                        exp_bad_piece + exp_pieces_going_bad[step_number]
                    )

            for step_number, machine in enumerate(lot_step_machines):
                dict_exp_bad[machine] += exp_num_bad_pieces[step_number]
                dict_going_bad[machine] += exp_pieces_going_bad[step_number]

    machine_info["exp_num_bad_pieces"] = machine_info["machine_name"].map(dict_exp_bad)
    machine_info["exp_pieces_going_bad"] = machine_info["machine_name"].map(
        dict_going_bad
    )
    machine_info["exp_num_good_pieces"] = (
        machine_info["exp_pieces_going_bad"] + machine_info["good_produced"]
    )
    return machine_info


def m_step(machine_info):
    machine_info["sum_exp"] = (
        machine_info["exp_num_bad_pieces"] + machine_info["exp_num_good_pieces"]
    )
    machine_info["em_yieldrate"] = (
        machine_info["exp_num_good_pieces"] / machine_info["sum_exp"]
    ).replace(np.nan, 0)
    return machine_info


def em_algorithm(source_data, mach_info, lot_info):
    mach_info["em_yieldrate"] = mach_info["init_yieldrate"]
    em_update = pd.DataFrame(data=None, columns=["last", "current", "diff"])

    for iters in range(MAX_EMA_ITERATIONS):
        mach_info["em_yieldrate"] = np.where(
            mach_info["em_yieldrate"] <= 0, EPSILON, mach_info["em_yieldrate"]
        )
        mach_info["ln_yieldrate"] = np.log(mach_info["em_yieldrate"])
        mach_info["prev_yieldrate"] = mach_info["em_yieldrate"]

        mach_info = e_step(source_data, mach_info)
        mach_info = m_step(mach_info)

        prev_yr = mach_info["prev_yieldrate"].values.copy()
        cur_yr = mach_info["em_yieldrate"].values.copy()
        diff = np.linalg.norm(prev_yr - cur_yr)
        em_update.loc[len(em_update)] = [prev_yr, cur_yr, diff]

        if diff <= 1.0e-3:
            break

    return mach_info, em_update, iters + 1


def create_report(machine_info, target_filename):
    machine_info = machine_info.sort_values("em_yieldrate")
    report = machine_info[["em_yieldrate", "exp_num_bad_pieces", "machine_name"]]
    report.columns = ["YieldRate", "BadPiece", "Machine"]
    report = report.reset_index(drop=True)

    pd.set_option("display.max_columns", None)
    report = report.round(5)
    report.to_csv(target_filename, sep=",", index=False)

    check = pd.read_csv(target_filename, index_col=0)
    print(
        "Saving %s Success" % target_filename
        if check.size == check.size
        else "Saving Report %s failed" % target_filename
    )
    pd.reset_option("^display.", silent=True)
    return report


def main(source_filename, report_filename):
    start = time.time()
    print("Process Start:", source_filename)

    raw_data = read_csv_files(source_filename)
    onehot_lot_last_step, machine_information, raw_data = get_onehot_machine(raw_data)
    lot_information = get_lot_information(raw_data)
    machine_information = get_machine_information(
        onehot_lot_last_step, machine_information, lot_information
    )
    machine_information, em_iter_res, iters = em_algorithm(
        raw_data, machine_information, lot_information
    )
    report = create_report(machine_information, report_filename)

    print("Process End:", source_filename)
    print("Iterations:", iters)
    cu.check_time(start, time.time())
    print()

    return (
        raw_data,
        onehot_lot_last_step,
        machine_information,
        lot_information,
        machine_information,
        em_iter_res,
        iters,
        report,
    )


if __name__ == "__main__":
    outputs = [
        ("test_case_1a.csv", "test_report.csv"),
        ("real_world_data.csv", "realworld_report.csv"),
    ]
    for source_filename, report_filename in outputs:
        _, _, _, _, _, _, _, report = main(source_filename, report_filename)
        print(report.head(20))
