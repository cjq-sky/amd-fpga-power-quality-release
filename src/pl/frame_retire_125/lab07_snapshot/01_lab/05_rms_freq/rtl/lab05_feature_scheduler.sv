`timescale 1ns/1ps
module lab05_feature_scheduler (
    input wire clk, reset, summary_pending,
    input wire [31:0] source_frame_id,
    input wire [41:0] sum_sq_ch1, sum_sq_ch2,
    input wire [15:0] peak_ch1, peak_ch2,
    input wire [10:0] first_crossing, last_crossing, crossing_count,
    input wire interval_anomaly,
    input wire frame_error, abort_seen, summary_overrun,
    output wire summary_ready,
    input wire result_ready,
    output reg result_valid,
    output reg [31:0] feature_frame_id,
    output reg [15:0] ch1_rms, ch2_rms, ch1_peak, ch2_peak, ch1_crest, ch2_crest,
    output reg [6:0] valid_mask,
    output reg [7:0] status,
    output reg [31:0] freq_ch1_mHz,
    output wire freq_ch1_valid,
    output reg frequency_crossing_anomaly,
    output reg result_overrun,
    output wire arithmetic_busy
);
    localparam [4:0] IDLE=0, R1_START=1, R1_WAIT=2, R2_START=3, R2_WAIT=4,
        C1_CHECK=5, D1_START=6, D1_WAIT=7, C1_START=8, C1_WAIT=9,
        C2_CHECK=10, D2_START=11, D2_WAIT=12, C2_START=13, C2_WAIT=14, PUBLISH=15,
        F_CHECK=16, F_START=17, F_WAIT=18;
    reg [4:0] state;
    reg [31:0] context_id;
    reg [41:0] s1, s2;
    reg [15:0] p1, p2, r1, r2, c1, c2;
    reg [6:0] context_mask;
    reg [31:0] crest_quotient;
    reg [10:0] f_first, f_last, f_count;
    reg f_anomaly;
    reg [31:0] f_result;
    wire [10:0] f_delta = f_last - f_first;
    wire [10:0] f_k = f_count == 11'd0 ? 11'd0 : f_count - 11'd1;
    // At most 1024 crossings => K<=1023 => numerator<=10,230,001,023<2^34.
    // Both multiply operands and addition terms are explicitly unsigned 34-bit.
    wire [33:0] f_product = 34'd10000000 * {23'd0, f_k};
    wire [33:0] f_numerator = f_product + {24'd0, f_delta[10:1]};
    wire sqrt_start = state==R1_START || state==R2_START || state==C1_START || state==C2_START;
    wire [31:0] sqrt_operand = state==R1_START ? {1'b0,s1[41:11]} :
                               state==R2_START ? {1'b0,s2[41:11]} : crest_quotient;
    wire sqrt_busy, sqrt_done;
    wire [15:0] sqrt_root;
    wire div_start = state==D1_START || state==D2_START || state==F_START;
    wire [31:0] peak_extended = state==D1_START ? {16'd0,p1} : {16'd0,p2};
    wire [31:0] peak_square = peak_extended * peak_extended;
    // P <= 32768 => P^2 <= 2^30. Concatenation exactly implements <<31.
    wire [61:0] crest_numerator = {peak_square[30:0],31'd0};
    wire [41:0] crest_denominator = state==D1_START ? s1 : s2;
    wire [61:0] div_numerator = state==F_START ? {28'd0,f_numerator} : crest_numerator;
    wire [41:0] div_denominator = state==F_START ? {31'd0,f_delta} : crest_denominator;
    wire div_busy, div_done, div_zero;
    wire [61:0] div_quotient;
    assign summary_ready = state==IDLE;
    assign arithmetic_busy = state!=IDLE;
    assign freq_ch1_valid = valid_mask[6];
    lab05_isqrt sqrt_engine(clk,reset,sqrt_start,sqrt_operand,sqrt_busy,sqrt_done,sqrt_root);
    lab05_udiv divider(clk,reset,div_start,div_numerator,div_denominator,
                       div_busy,div_done,div_zero,div_quotient);
    always @(posedge clk) begin
        if (reset) begin
            state<=IDLE; context_id<=0; s1<=0; s2<=0; p1<=0; p2<=0;
            r1<=0; r2<=0; c1<=0; c2<=0; context_mask<=0; crest_quotient<=0;
            f_first<=0; f_last<=0; f_count<=0; f_anomaly<=0; f_result<=0;
            freq_ch1_mHz<=0; frequency_crossing_anomaly<=0;
            result_valid<=0; feature_frame_id<=0; ch1_rms<=0; ch2_rms<=0;
            ch1_peak<=0; ch2_peak<=0; ch1_crest<=0; ch2_crest<=0;
            valid_mask<=0; status<=0; result_overrun<=0;
        end else begin
            if (result_valid && result_ready) result_valid<=0;
            case (state)
                IDLE: if (summary_pending) begin
                    context_id<=source_frame_id; s1<=sum_sq_ch1; s2<=sum_sq_ch2;
                    p1<=peak_ch1; p2<=peak_ch2; r1<=0; r2<=0; c1<=0; c2<=0;
                    context_mask<=7'h0f; crest_quotient<=0; state<=R1_START;
                    f_first<=first_crossing; f_last<=last_crossing; f_count<=crossing_count;
                    f_anomaly<=interval_anomaly; f_result<=0;
                end
                R1_START: state<=R1_WAIT;
                R1_WAIT: if (sqrt_done) begin r1<=sqrt_root; state<=R2_START; end
                R2_START: state<=R2_WAIT;
                R2_WAIT: if (sqrt_done) begin r2<=sqrt_root; state<=C1_CHECK; end
                C1_CHECK: state<=(s1!=42'd0 && r1!=16'd0) ? D1_START : C2_CHECK;
                D1_START: state<=D1_WAIT;
                D1_WAIT: if (div_done) begin crest_quotient<=div_quotient[31:0]; state<=C1_START; end
                C1_START: state<=C1_WAIT;
                C1_WAIT: if (sqrt_done) begin c1<=sqrt_root; context_mask[4]<=1; state<=C2_CHECK; end
                C2_CHECK: state<=(s2!=42'd0 && r2!=16'd0) ? D2_START : F_CHECK;
                D2_START: state<=D2_WAIT;
                D2_WAIT: if (div_done) begin crest_quotient<=div_quotient[31:0]; state<=C2_START; end
                C2_START: state<=C2_WAIT;
                C2_WAIT: if (sqrt_done) begin c2<=sqrt_root; context_mask[5]<=1; state<=F_CHECK; end
                F_CHECK: state<=(f_count>=11'd2 && f_delta!=11'd0 && !f_anomaly) ? F_START : PUBLISH;
                F_START: state<=F_WAIT;
                F_WAIT: if (div_done) begin
                    if (!div_zero && div_quotient>=62'd40000 && div_quotient<=62'd120000) begin
                        f_result<=div_quotient[31:0]; context_mask[6]<=1;
                    end
                    state<=PUBLISH;
                end
                PUBLISH: begin
                    if (!result_valid || result_ready) begin
                        result_valid<=1; feature_frame_id<=context_id;
                        ch1_rms<=r1; ch2_rms<=r2; ch1_peak<=p1; ch2_peak<=p2;
                        ch1_crest<=c1; ch2_crest<=c2; valid_mask<=context_mask;
                        freq_ch1_mHz<=f_result; frequency_crossing_anomaly<=f_anomaly;
                        // Atomic diagnostic snapshot; live sticky outputs remain separate.
                        status<={2'd0,f_anomaly,result_overrun,summary_overrun,abort_seen,frame_error,1'b1};
                    end else result_overrun<=1;
                    state<=IDLE;
                end
                default: state<=IDLE;
            endcase
        end
    end
endmodule
