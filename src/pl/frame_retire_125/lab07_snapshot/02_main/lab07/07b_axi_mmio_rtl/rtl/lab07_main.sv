`timescale 1ns/1ps
// PRE-LAB07 PL-only functional integration. All internal logic uses 125 MHz.
module lab07_main #(
    parameter ROM_FILE = "hann_q17.hex"
) (
    input wire clk_125mhz,
    input wire [15:0] ad_data,
    input wire ad_busy,
    input wire ad_frstdata,
    output wire ad_convst,
    output wire ad_reset,
    output wire ad_cs_n,
    output wire ad_rd_n,
    output wire sample_valid,
    output wire [10:0] sample_index,
    output wire [31:0] sample_frame_id,
    output wire signed [15:0] sample_ch1_code,
    output wire signed [15:0] sample_ch2_code,
    output wire [1:0] sample_channel_valid,
    output wire sample_abort,
    output wire feature_snapshot_valid,
    output wire [31:0] feature_snapshot_seq,
    output wire [31:0] feature_frame_id,
    output wire [8:0] feature_valid_mask,
    output wire feature_acquisition_valid,
    output wire [7:0] feature_time_status,
    output wire [31:0] feature_spectral_status,
    output wire [31:0] feature_numeric_status,
    output wire [3:0] feature_formal_identity,
    output wire [15:0] ch1_rms, ch2_rms,
    output wire [15:0] ch1_peak, ch2_peak,
    output wire [15:0] ch1_crest, ch2_crest,
    output wire [31:0] frequency_ch1_mhz,
    output wire [31:0] ch1_h1, ch1_h3, ch1_h5, ch1_h7, ch1_h9,
    output wire [31:0] ch2_h1, ch2_h3, ch2_h5, ch2_h7, ch2_h9,
    output wire [31:0] ch1_thd, ch2_thd,
    output wire acquisition_fault_live,
    output wire [7:0] acquisition_fault_code_live,
    output wire branch_mismatch_sticky,
    output wire order_unknown_sticky,
    output wire [31:0] last_mismatch_time_id,
    output wire [31:0] last_mismatch_spectral_id,
    output wire time_waiting_for_spectral,
    output wire spectral_waiting_for_time,
    output wire time_output_held,
    output wire spectral_output_held,
    output wire lab05_summary_overrun_live,
    output wire lab05_result_overrun_live,
    output reg lab06_bank_overrun_sticky,
    output reg lab06_frame_error_sticky,
    output reg lab06_protocol_error_sticky,
    output wire [31:0] last_successful_feature_frame_id,
    output wire [31:0] snapshot_update_counter,
    input wire raw_ack_valid,
    input wire raw_ack_bank_id,
    input wire [31:0] raw_ack_token,
    input wire raw_read_en,
    input wire raw_read_bank_id,
    input wire [10:0] raw_read_index,
    output wire [31:0] raw_read_data,
    output wire raw_read_valid,
    output wire raw_frame_valid,
    output wire raw_bank_id,
    output wire [31:0] raw_frame_id,
    output wire [7:0] raw_status,
    output wire [31:0] raw_owner_token,
    output wire raw_drop_sticky,
    output wire [31:0] raw_drop_count,
    output wire raw_protocol_sticky,
    output wire raw_ack_error_sticky,
    output wire raw_token_exhausted_sticky,
    output wire [7:0] raw_bank_states
);
    wire [15:0] adc_ch1, adc_ch2;
    wire dual_sample_valid, busy_timeout, frstdata_mismatch;
    ad7606_controller u_controller (
        .clk_125mhz(clk_125mhz), .ad_data(ad_data), .ad_busy(ad_busy),
        .ad_frstdata(ad_frstdata), .ad_convst(ad_convst), .ad_reset(ad_reset),
        .ad_cs_n(ad_cs_n), .ad_rd_n(ad_rd_n),
        .sample_ch1(adc_ch1), .sample_ch2(adc_ch2),
        .dual_sample_valid(dual_sample_valid), .busy_timeout(busy_timeout),
        .frstdata_mismatch(frstdata_mismatch)
    );
    wire accepted_sample_valid;
    wire [10:0] accepted_index;
    wire [31:0] accepted_frame_id;
    lab04_raw_transport u_transport (
        .clk(clk_125mhz), .sample_ch1(adc_ch1), .sample_ch2(adc_ch2),
        .dual_sample_valid(dual_sample_valid), .ad_convst(ad_convst),
        .busy_timeout(busy_timeout), .frstdata_mismatch(frstdata_mismatch),
        .sample_write_commit(accepted_sample_valid),
        .raw_sample_index(accepted_index), .raw_frame_id(accepted_frame_id),
        .acquisition_fault(acquisition_fault_live),
        .fault_code(acquisition_fault_code_live)
    );
    assign sample_valid = accepted_sample_valid;
    assign sample_index = accepted_index;
    assign sample_frame_id = accepted_frame_id;
    assign sample_ch1_code = $signed(adc_ch1);
    assign sample_ch2_code = $signed(adc_ch2);
    assign sample_channel_valid = accepted_sample_valid ? 2'b11 : 2'b00;
    assign sample_abort = acquisition_fault_live;
    wire source_frame_complete = accepted_sample_valid && accepted_index==11'd2047;

    wire time_sample_valid, time_abort;
    wire [10:0] time_index;
    wire [31:0] time_input_fid;
    wire signed [15:0] time_ch1, time_ch2;
    lab05_sample_boundary u_time_boundary (
        .clk(clk_125mhz), .reset(ad_reset),
        .sample_valid(accepted_sample_valid), .frame_abort(acquisition_fault_live),
        .sample_index(accepted_index), .frame_id(accepted_frame_id),
        .ch1_code($signed(adc_ch1)), .ch2_code($signed(adc_ch2)),
        .sample_valid_q(time_sample_valid), .frame_abort_q(time_abort),
        .sample_index_q(time_index), .frame_id_q(time_input_fid),
        .ch1_code_q(time_ch1), .ch2_code_q(time_ch2)
    );
    wire time_result_valid, time_result_ready;
    wire [31:0] time_result_fid, time_frequency;
    wire [15:0] time_ch1_rms, time_ch2_rms, time_ch1_peak, time_ch2_peak;
    wire [15:0] time_ch1_crest, time_ch2_crest;
    wire [6:0] time_valid_mask;
    wire [7:0] time_status;
    lab05_basic_features_top u_time (
        .clk(clk_125mhz), .reset(ad_reset), .sample_valid(time_sample_valid),
        .sample_index(time_index), .frame_id(time_input_fid),
        .ch1_code(time_ch1), .ch2_code(time_ch2), .frame_abort(time_abort),
        .result_ready(time_result_ready), .result_valid(time_result_valid),
        .feature_frame_id(time_result_fid), .ch1_rms(time_ch1_rms),
        .ch2_rms(time_ch2_rms), .ch1_peak(time_ch1_peak),
        .ch2_peak(time_ch2_peak), .ch1_crest(time_ch1_crest),
        .ch2_crest(time_ch2_crest), .freq_ch1_mHz(time_frequency),
        .valid_mask(time_valid_mask), .status(time_status),
        .summary_overrun(lab05_summary_overrun_live),
        .result_overrun(lab05_result_overrun_live)
    );
    wire [127:0] time_payload = {time_frequency,time_ch2_crest,time_ch1_crest,
                                 time_ch2_peak,time_ch1_peak,time_ch2_rms,time_ch1_rms};

    wire spectral_sample_valid, spectral_abort;
    wire [10:0] spectral_index;
    wire [31:0] spectral_input_fid;
    wire signed [15:0] spectral_ch1, spectral_ch2;
    lab06_sample_boundary u_spectral_boundary (
        .clk(clk_125mhz), .reset(ad_reset),
        .sample_valid(accepted_sample_valid), .frame_abort(acquisition_fault_live),
        .sample_index(accepted_index), .frame_id(accepted_frame_id),
        .ch1_code($signed(adc_ch1)), .ch2_code($signed(adc_ch2)),
        .sample_valid_q(spectral_sample_valid), .frame_abort_q(spectral_abort),
        .sample_index_q(spectral_index), .frame_id_q(spectral_input_fid),
        .ch1_code_q(spectral_ch1), .ch2_code_q(spectral_ch2)
    );
    wire spectral_publication_valid, spectral_publication_ready;
    wire [31:0] spectral_result_fid, spectral_status;
    wire [1:0] spectral_valid_mask;
    wire [319:0] spectral_harmonics, spectral_numeric_harmonics;
    wire [31:0] spectral_numeric_status;
    wire [3:0] spectral_formal_identity;
    wire [63:0] spectral_thd, spectral_numeric_thd;
    wire spectral_frame_error, spectral_protocol_error, spectral_bank_overrun;
    lab07_spectral_publication_top #(.ROM_FILE(ROM_FILE)) u_spectral (
        .clk(clk_125mhz), .reset(ad_reset), .abort(spectral_abort),
        .sample_valid(spectral_sample_valid), .source_frame_id(spectral_input_fid),
        .sample_index(spectral_index), .ch1(spectral_ch1), .ch2(spectral_ch2),
        .identity_ch1(2'b00), .identity_ch2(2'b00),
        .threshold_ch1_q24(64'd68508759685),
        .threshold_ch2_q24(64'd68508759685), .extreme(2'b00),
        .source_error(spectral_abort), .frame_error(spectral_frame_error),
        .protocol_error(spectral_protocol_error), .bank_overrun(spectral_bank_overrun),
        .publication_valid(spectral_publication_valid),
        .publication_ready(spectral_publication_ready),
        .result_frame_id(spectral_result_fid), .status(spectral_status),
        .result_valid(),
        .spectral_numeric_status(spectral_numeric_status),
        .formal_identity(spectral_formal_identity),
        .raw_harmonics_q16(spectral_numeric_harmonics),
        .raw_thd_q16(spectral_numeric_thd), .harmonics_q16(spectral_harmonics),
        .thd_odd_3_5_7_9_q16(spectral_thd)
    );
    assign spectral_valid_mask = {spectral_numeric_status[16],spectral_numeric_status[0]};
    // Invalid whole-channel zero-select; mirror/formal core outputs remain intact.
    wire [383:0] spectral_payload = {
        spectral_valid_mask[1] ? spectral_numeric_thd[63:32] : 32'd0,
        spectral_valid_mask[0] ? spectral_numeric_thd[31:0] : 32'd0,
        spectral_valid_mask[1] ? spectral_numeric_harmonics[319:160] : 160'd0,
        spectral_valid_mask[0] ? spectral_numeric_harmonics[159:0] : 160'd0};
    always @(posedge clk_125mhz) begin
        if (ad_reset) begin
            lab06_bank_overrun_sticky <= 0;
            lab06_frame_error_sticky <= 0;
            lab06_protocol_error_sticky <= 0;
        end else begin
            if (spectral_bank_overrun) lab06_bank_overrun_sticky <= 1;
            if (spectral_frame_error) lab06_frame_error_sticky <= 1;
            if (spectral_protocol_error) lab06_protocol_error_sticky <= 1;
        end
    end

    wire combined_valid;
    wire [31:0] combined_fid;
    wire [127:0] combined_time_payload;
    wire [383:0] combined_spectral_payload;
    wire [8:0] combined_mask;
    wire [7:0] combined_time_status;
    wire [31:0] combined_spectral_status, combined_numeric_status;
    wire [3:0] combined_formal_identity;
    lab07_feature_aggregator u_aggregator (
        .clk(clk_125mhz), .reset(ad_reset),
        .source_frame_complete(source_frame_complete),
        .acquisition_fault_live(acquisition_fault_live),
        .time_result_valid(time_result_valid), .time_result_ready(time_result_ready),
        .time_frame_id(time_result_fid), .time_payload(time_payload),
        .time_valid_mask(time_valid_mask), .time_status(time_status),
        .spectral_result_valid(spectral_publication_valid),
        .spectral_result_ready(spectral_publication_ready),
        .spectral_frame_id(spectral_result_fid), .spectral_payload(spectral_payload),
        .spectral_valid_mask(spectral_valid_mask), .spectral_status(spectral_status),
        .spectral_numeric_status(spectral_numeric_status),
        .spectral_formal_identity(spectral_formal_identity),
        .combined_numeric_status(combined_numeric_status),
        .combined_formal_identity(combined_formal_identity),
        .combined_result_valid(combined_valid), .combined_frame_id(combined_fid),
        .combined_time_payload(combined_time_payload),
        .combined_spectral_payload(combined_spectral_payload),
        .combined_valid_mask(combined_mask),
        .combined_time_status(combined_time_status),
        .combined_spectral_status(combined_spectral_status),
        .branch_mismatch_sticky(branch_mismatch_sticky),
        .order_unknown_sticky(order_unknown_sticky),
        .last_mismatch_time_id(last_mismatch_time_id),
        .last_mismatch_spectral_id(last_mismatch_spectral_id),
        .time_waiting_for_spectral(time_waiting_for_spectral),
        .spectral_waiting_for_time(spectral_waiting_for_time),
        .time_output_held(time_output_held),
        .spectral_output_held(spectral_output_held)
    );
    wire [127:0] frozen_time;
    wire [383:0] frozen_spectral;
    lab07_feature_snapshot_bank u_snapshot (
        .clk(clk_125mhz), .reset(ad_reset), .combined_result_valid(combined_valid),
        .combined_frame_id(combined_fid), .combined_time_payload(combined_time_payload),
        .combined_spectral_payload(combined_spectral_payload),
        .combined_valid_mask(combined_mask),
        .combined_time_status(combined_time_status),
        .combined_spectral_status(combined_spectral_status),
        .combined_numeric_status(combined_numeric_status),
        .combined_formal_identity(combined_formal_identity),
        .feature_numeric_status(feature_numeric_status),
        .feature_formal_identity(feature_formal_identity),
        .snapshot_valid(feature_snapshot_valid), .snapshot_seq(feature_snapshot_seq),
        .feature_frame_id(feature_frame_id), .feature_time_payload(frozen_time),
        .feature_spectral_payload(frozen_spectral),
        .feature_valid_mask(feature_valid_mask),
        .feature_time_status(feature_time_status),
        .feature_spectral_status(feature_spectral_status),
        .feature_acquisition_valid(feature_acquisition_valid)
    );
    assign {frequency_ch1_mhz,ch2_crest,ch1_crest,ch2_peak,ch1_peak,
            ch2_rms,ch1_rms} = frozen_time;
    assign {ch2_thd,ch1_thd,ch2_h9,ch2_h7,ch2_h5,ch2_h3,ch2_h1,
            ch1_h9,ch1_h7,ch1_h5,ch1_h3,ch1_h1} = frozen_spectral;
    assign last_successful_feature_frame_id = feature_frame_id;
    assign snapshot_update_counter = feature_snapshot_seq;

    raw_frame_bank_manager u_raw (
        .clk(clk_125mhz), .reset(ad_reset),
        .sample_valid(accepted_sample_valid), .sample_index(accepted_index),
        .sample_frame_id(accepted_frame_id), .ch1_code($signed(adc_ch1)),
        .ch2_code($signed(adc_ch2)), .frame_abort(acquisition_fault_live),
        .raw_ack_valid(raw_ack_valid), .raw_ack_bank_id(raw_ack_bank_id),
        .raw_ack_token(raw_ack_token), .raw_read_en(raw_read_en),
        .raw_read_bank_id(raw_read_bank_id), .raw_read_index(raw_read_index),
        .raw_read_data(raw_read_data), .raw_read_valid(raw_read_valid),
        .raw_frame_valid(raw_frame_valid), .raw_bank_id(raw_bank_id),
        .raw_frame_id(raw_frame_id), .raw_status(raw_status),
        .raw_owner_token(raw_owner_token), .raw_drop_sticky(raw_drop_sticky),
        .raw_drop_count(raw_drop_count), .raw_protocol_sticky(raw_protocol_sticky),
        .raw_ack_error_sticky(raw_ack_error_sticky),
        .raw_token_exhausted_sticky(raw_token_exhausted_sticky),
        .raw_bank_states(raw_bank_states)
    );
endmodule
