`timescale 1ns/1ps
// One PL edge atomically replaces every field of the published tuple.
module lab07_feature_snapshot_bank (
    input wire clk,
    input wire reset,
    input wire combined_result_valid,
    input wire [31:0] combined_frame_id,
    input wire [127:0] combined_time_payload,
    input wire [383:0] combined_spectral_payload,
    input wire [8:0] combined_valid_mask,
    input wire [7:0] combined_time_status,
    input wire [31:0] combined_spectral_status,
    input wire [31:0] combined_numeric_status,
    input wire [3:0] combined_formal_identity,
    output reg snapshot_valid,
    output reg [31:0] snapshot_seq,
    output reg [31:0] feature_frame_id,
    output reg [127:0] feature_time_payload,
    output reg [383:0] feature_spectral_payload,
    output reg [8:0] feature_valid_mask,
    output reg [7:0] feature_time_status,
    output reg [31:0] feature_spectral_status,
    output reg [31:0] feature_numeric_status,
    output reg [3:0] feature_formal_identity,
    output reg feature_acquisition_valid
);
    always @(posedge clk) begin
        if (reset) begin
            snapshot_valid <= 1'b0;
            snapshot_seq <= 0;
            feature_frame_id <= 0;
            feature_time_payload <= 0;
            feature_spectral_payload <= 0;
            feature_valid_mask <= 0;
            feature_time_status <= 0;
            feature_spectral_status <= 0;
            feature_numeric_status <= 0; feature_formal_identity <= 0;
            feature_acquisition_valid <= 1'b0;
        end else if (combined_result_valid) begin
            snapshot_valid <= 1'b1;
            snapshot_seq <= snapshot_seq + 1'b1;
            feature_frame_id <= combined_frame_id;
            feature_time_payload <= combined_time_payload;
            feature_spectral_payload <= combined_spectral_payload;
            feature_valid_mask <= combined_valid_mask;
            feature_time_status <= combined_time_status;
            feature_spectral_status <= combined_spectral_status;
            feature_numeric_status <= combined_numeric_status;
            feature_formal_identity <= combined_formal_identity;
            feature_acquisition_valid <= 1'b1;
        end
    end
endmodule
