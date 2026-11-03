`timescale 1ns/1ps
module lab05_basic_features_top (
    input wire clk, reset, sample_valid,
    input wire [10:0] sample_index,
    input wire [31:0] frame_id,
    input wire signed [15:0] ch1_code, ch2_code,
    input wire frame_abort, result_ready,
    output wire result_valid,
    output wire [31:0] feature_frame_id,
    output wire [15:0] ch1_rms, ch2_rms, ch1_peak, ch2_peak, ch1_crest, ch2_crest,
    output wire [6:0] valid_mask,
    output wire [7:0] status,
    output wire [31:0] freq_ch1_mHz,
    output wire freq_ch1_valid, frequency_crossing_anomaly,
    output wire summary_overrun, result_overrun, frame_error, abort_seen,
    output wire summary_pending, arithmetic_busy
);
    wire summary_ready;
    wire [31:0] source_frame_id;
    wire [41:0] sum_sq_ch1, sum_sq_ch2;
    wire [15:0] peak_ch1, peak_ch2;
    wire [10:0] first_crossing, last_crossing, crossing_count, interval_min, interval_max;
    wire interval_anomaly;
    lab05_frame_stats stats (
        .clk(clk),.reset(reset),.sample_valid(sample_valid),.frame_abort(frame_abort),
        .sample_index(sample_index),.frame_id(frame_id),.ch1_code(ch1_code),.ch2_code(ch2_code),
        .summary_ready(summary_ready),.summary_pending(summary_pending),.source_frame_id(source_frame_id),
        .sum_sq_ch1(sum_sq_ch1),.sum_sq_ch2(sum_sq_ch2),.peak_ch1(peak_ch1),.peak_ch2(peak_ch2),
        .summary_overrun(summary_overrun),.frame_error(frame_error),.abort_seen(abort_seen),
        .first_crossing(first_crossing),.last_crossing(last_crossing),.crossing_count(crossing_count),
        .interval_min(interval_min),.interval_max(interval_max),.interval_anomaly(interval_anomaly)
    );
    lab05_feature_scheduler scheduler (
        .clk(clk),.reset(reset),.summary_pending(summary_pending),.summary_ready(summary_ready),
        .source_frame_id(source_frame_id),.sum_sq_ch1(sum_sq_ch1),.sum_sq_ch2(sum_sq_ch2),
        .peak_ch1(peak_ch1),.peak_ch2(peak_ch2),.frame_error(frame_error),.abort_seen(abort_seen),
        .first_crossing(first_crossing),.last_crossing(last_crossing),.crossing_count(crossing_count),
        .interval_anomaly(interval_anomaly),
        .summary_overrun(summary_overrun),.result_ready(result_ready),.result_valid(result_valid),
        .feature_frame_id(feature_frame_id),.ch1_rms(ch1_rms),.ch2_rms(ch2_rms),
        .ch1_peak(ch1_peak),.ch2_peak(ch2_peak),.ch1_crest(ch1_crest),.ch2_crest(ch2_crest),
        .valid_mask(valid_mask),.status(status),.result_overrun(result_overrun),.arithmetic_busy(arithmetic_busy),
        .freq_ch1_mHz(freq_ch1_mHz),.freq_ch1_valid(freq_ch1_valid),
        .frequency_crossing_anomaly(frequency_crossing_anomaly)
    );
endmodule
