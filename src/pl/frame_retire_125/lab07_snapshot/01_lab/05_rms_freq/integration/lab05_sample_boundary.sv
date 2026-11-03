`timescale 1ns/1ps
// One atomic, synchronous stage on the read-only analysis branch.
// Capture idle metadata and abort too; no upstream backpressure or gating.
module lab05_sample_boundary (
    input wire clk, reset,
    input wire sample_valid, frame_abort,
    input wire [10:0] sample_index,
    input wire [31:0] frame_id,
    input wire signed [15:0] ch1_code, ch2_code,
    output reg sample_valid_q, frame_abort_q,
    output reg [10:0] sample_index_q,
    output reg [31:0] frame_id_q,
    output reg signed [15:0] ch1_code_q, ch2_code_q
);
    always @(posedge clk) begin
        if (reset) begin
            sample_valid_q <= 1'b0; frame_abort_q <= 1'b0;
            sample_index_q <= 11'd0; frame_id_q <= 32'd0;
            ch1_code_q <= 16'sd0; ch2_code_q <= 16'sd0;
        end else begin
            sample_valid_q <= sample_valid; frame_abort_q <= frame_abort;
            sample_index_q <= sample_index; frame_id_q <= frame_id;
            ch1_code_q <= ch1_code; ch2_code_q <= ch2_code;
        end
    end
endmodule
