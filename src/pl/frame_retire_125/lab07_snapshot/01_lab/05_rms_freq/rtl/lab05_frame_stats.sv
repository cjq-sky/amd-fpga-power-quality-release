`timescale 1ns/1ps
module lab05_frame_stats (
    input wire clk, reset, sample_valid, frame_abort,
    input wire [10:0] sample_index,
    input wire [31:0] frame_id,
    input wire signed [15:0] ch1_code, ch2_code,
    input wire summary_ready,
    output reg summary_pending,
    output reg [31:0] source_frame_id,
    output reg [41:0] sum_sq_ch1, sum_sq_ch2,
    output reg [15:0] peak_ch1, peak_ch2,
    output reg summary_overrun, frame_error, abort_seen,
    output reg [10:0] first_crossing, last_crossing, crossing_count,
    output reg [10:0] interval_min, interval_max,
    output reg interval_anomaly
);
    reg active;
    reg [10:0] expected_index;
    reg [31:0] working_frame_id;
    reg [41:0] working_sum1, working_sum2;
    reg [15:0] working_peak1, working_peak2;
    wire signed [16:0] ext1 = {ch1_code[15], ch1_code};
    wire signed [16:0] ext2 = {ch2_code[15], ch2_code};
    // Both multiply operands and product have explicit signed 34-bit width.
    wire signed [33:0] mul1 = {{17{ext1[16]}}, ext1};
    wire signed [33:0] mul2 = {{17{ext2[16]}}, ext2};
    wire signed [33:0] product1 = mul1 * mul1;
    wire signed [33:0] product2 = mul2 * mul2;
    // Nonnegative product <= 2^30; all upper bits are provably zero.
    wire [30:0] square1 = product1[30:0];
    wire [30:0] square2 = product2[30:0];
    wire [16:0] mag_ext1 = ext1[16] ? -ext1 : ext1;
    wire [16:0] mag_ext2 = ext2[16] ? -ext2 : ext2;
    wire [15:0] mag1 = mag_ext1[15:0];
    wire [15:0] mag2 = mag_ext2[15:0];
    // Fix2: exactly one atomic derived token. Abort is independent of valid.
    // Every cycle captures its context; reset flushes both sample and control.
    reg derived_valid, derived_abort, ch1_negative;
    reg [10:0] derived_index;
    reg [31:0] derived_frame_id;
    reg [30:0] square_ch1, square_ch2;
    reg [15:0] abs_ch1, abs_ch2;
    always @(posedge clk) begin
        if (reset) begin
            derived_valid <= 0; derived_abort <= 0; ch1_negative <= 0;
            derived_index <= 0; derived_frame_id <= 0;
            square_ch1 <= 0; square_ch2 <= 0; abs_ch1 <= 0; abs_ch2 <= 0;
        end else begin
            derived_valid <= sample_valid; derived_abort <= frame_abort;
            derived_index <= sample_index; derived_frame_id <= frame_id;
            square_ch1 <= square1; square_ch2 <= square2;
            abs_ch1 <= mag1; abs_ch2 <= mag2; ch1_negative <= ch1_code[15];
        end
    end

    wire [41:0] next_sum1 = working_sum1 + {11'd0, square_ch1};
    wire [41:0] next_sum2 = working_sum2 + {11'd0, square_ch2};
    wire [15:0] next_peak1 = abs_ch1 > working_peak1 ? abs_ch1 : working_peak1;
    wire [15:0] next_peak2 = abs_ch2 > working_peak2 ? abs_ch2 : working_peak2;

    // Frequency shares the existing checker acceptance decisions. No history
    // crosses frame boundaries, and idle clocks do not change previous_negative.
    reg previous_negative;
    reg previous_sample_valid;
    reg [10:0] working_first, working_last, working_count, previous_crossing;
    reg [10:0] working_interval_min, working_interval_max;
    reg working_anomaly;
    wire accepted = derived_valid && active && !derived_abort &&
                    derived_frame_id == working_frame_id && derived_index == expected_index;
    wire start_frame = derived_valid && !active && !derived_abort && derived_index == 11'd0;
    wire end_frame = accepted && derived_index == 11'd2047;
    wire discard_frame = derived_abort || (derived_valid && active &&
                         (derived_frame_id != working_frame_id || derived_index != expected_index));
    wire crossing = previous_sample_valid && previous_negative && !ch1_negative;
    wire [10:0] crossing_interval = derived_index - previous_crossing;
    wire subsequent_crossing = crossing && working_count != 11'd0;
    wire [10:0] next_first = crossing && working_count == 11'd0 ? derived_index : working_first;
    wire [10:0] next_last = crossing ? derived_index : working_last;
    wire [10:0] next_count = crossing ? working_count + 11'd1 : working_count;
    wire [10:0] next_interval_min = subsequent_crossing &&
        (working_count == 11'd1 || crossing_interval < working_interval_min) ?
        crossing_interval : working_interval_min;
    wire [10:0] next_interval_max = subsequent_crossing &&
        (working_count == 11'd1 || crossing_interval > working_interval_max) ?
        crossing_interval : working_interval_max;
    wire next_anomaly = working_anomaly || (subsequent_crossing &&
                        (crossing_interval < 11'd83 || crossing_interval > 11'd250));
    always @(posedge clk) begin
        if (reset) begin
            previous_negative <= 0; previous_sample_valid <= 0; previous_crossing <= 0;
            working_first <= 0; working_last <= 0; working_count <= 0;
            working_interval_min <= 0; working_interval_max <= 0; working_anomaly <= 0;
            first_crossing <= 0; last_crossing <= 0; crossing_count <= 0;
            interval_min <= 0; interval_max <= 0; interval_anomaly <= 0;
        end else begin
            if (discard_frame || start_frame || end_frame) begin
                previous_negative <= start_frame ? ch1_negative : 1'b0;
                previous_sample_valid <= start_frame;
                previous_crossing <= 0; working_first <= 0; working_last <= 0; working_count <= 0;
                working_interval_min <= 0; working_interval_max <= 0; working_anomaly <= 0;
            end else if (accepted) begin
                previous_negative <= ch1_negative; previous_sample_valid <= 1;
                previous_crossing <= crossing ? derived_index : previous_crossing;
                working_first <= next_first; working_last <= next_last; working_count <= next_count;
                working_interval_min <= next_interval_min; working_interval_max <= next_interval_max;
                working_anomaly <= next_anomaly;
            end
            if (end_frame && (!summary_pending || summary_ready)) begin
                // next_* includes a crossing at index2047, just like next_sum.
                first_crossing <= next_first; last_crossing <= next_last; crossing_count <= next_count;
                interval_min <= next_interval_min; interval_max <= next_interval_max;
                interval_anomaly <= next_anomaly;
            end
        end
    end

    always @(posedge clk) begin
        if (reset) begin
            active <= 0; expected_index <= 0; working_frame_id <= 0;
            working_sum1 <= 0; working_sum2 <= 0;
            working_peak1 <= 0; working_peak2 <= 0;
            summary_pending <= 0; source_frame_id <= 0;
            sum_sq_ch1 <= 0; sum_sq_ch2 <= 0; peak_ch1 <= 0; peak_ch2 <= 0;
            summary_overrun <= 0; frame_error <= 0; abort_seen <= 0;
        end else begin
            if (summary_pending && summary_ready) summary_pending <= 0;
            if (derived_abort) begin
                active <= 0; expected_index <= 0; working_frame_id <= 0;
                working_sum1 <= 0; working_sum2 <= 0;
                working_peak1 <= 0; working_peak2 <= 0;
                abort_seen <= 1;
                if (active) frame_error <= 1;
            end else if (derived_valid) begin
                if (!active) begin
                    if (derived_index == 11'd0) begin
                        active <= 1; expected_index <= 11'd1; working_frame_id <= derived_frame_id;
                        working_sum1 <= {11'd0, square_ch1}; working_sum2 <= {11'd0, square_ch2};
                        working_peak1 <= abs_ch1; working_peak2 <= abs_ch2;
                    end
                end else if (derived_frame_id != working_frame_id || derived_index != expected_index) begin
                    // Consume fault event, including index=0; resync on a later index=0.
                    active <= 0; expected_index <= 0; working_frame_id <= 0;
                    working_sum1 <= 0; working_sum2 <= 0;
                    working_peak1 <= 0; working_peak2 <= 0; frame_error <= 1;
                end else if (derived_index == 11'd2047) begin
                    active <= 0; expected_index <= 0; working_frame_id <= 0;
                    working_sum1 <= 0; working_sum2 <= 0;
                    working_peak1 <= 0; working_peak2 <= 0;
                    if (!summary_pending || summary_ready) begin
                        summary_pending <= 1; source_frame_id <= working_frame_id;
                        sum_sq_ch1 <= next_sum1; sum_sq_ch2 <= next_sum2;
                        peak_ch1 <= next_peak1; peak_ch2 <= next_peak2;
                    end else summary_overrun <= 1;
                end else begin
                    expected_index <= expected_index + 11'd1;
                    working_sum1 <= next_sum1; working_sum2 <= next_sum2;
                    working_peak1 <= next_peak1; working_peak2 <= next_peak2;
                end
            end
        end
    end
endmodule
