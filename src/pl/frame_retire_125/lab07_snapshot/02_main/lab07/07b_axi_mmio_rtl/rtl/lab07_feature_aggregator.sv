`timescale 1ns/1ps
// Two ordered, one-entry result queues. Loss of a branch result is diagnosed
// upstream; this block never combines different source-frame IDs.
module lab07_feature_aggregator (
    input  wire         clk,
    input  wire         reset,
    input  wire         source_frame_complete,
    input  wire         acquisition_fault_live,
    input  wire         time_result_valid,
    output wire         time_result_ready,
    input  wire [31:0]  time_frame_id,
    input  wire [127:0] time_payload,
    input  wire [6:0]   time_valid_mask,
    input  wire [7:0]   time_status,
    input  wire         spectral_result_valid,
    output wire         spectral_result_ready,
    input  wire [31:0]  spectral_frame_id,
    input  wire [383:0] spectral_payload,
    input  wire [1:0]   spectral_valid_mask,
    input  wire [31:0]  spectral_status,
    input wire [31:0] spectral_numeric_status,
    input wire [3:0] spectral_formal_identity,
    output wire         combined_result_valid,
    output wire [31:0]  combined_frame_id,
    output wire [127:0] combined_time_payload,
    output wire [383:0] combined_spectral_payload,
    output wire [8:0]   combined_valid_mask,
    output wire [7:0]   combined_time_status,
    output wire [31:0]  combined_spectral_status,
    output wire [31:0] combined_numeric_status,
    output wire [3:0] combined_formal_identity,
    output reg          branch_mismatch_sticky,
    output reg          order_unknown_sticky,
    output reg  [31:0]  last_mismatch_time_id,
    output reg  [31:0]  last_mismatch_spectral_id,
    output wire         time_waiting_for_spectral,
    output wire         spectral_waiting_for_time,
    output wire         time_output_held,
    output wire         spectral_output_held
);
    localparam [31:0] HALF_SPACE = 32'h8000_0000;
    reg time_pending, spectral_pending;
    reg [31:0] time_pending_id, spectral_pending_id;
    reg [127:0] time_pending_payload;
    reg [383:0] spectral_pending_payload;
    reg [6:0] time_pending_mask;
    reg [1:0] spectral_pending_mask;
    reg [7:0] time_pending_status;
    reg [31:0] spectral_pending_status;
    reg [31:0] numeric_pending_status;
    reg [3:0] formal_pending_identity;

    // Age begins when a branch first holds valid without ready. It is copied
    // into the pending slot on handshake and is NEVER restarted at capture.
    // Units are completed Lab04 frames, not clocks or algorithm latency.
    reg [31:0] time_output_age, spectral_output_age;
    reg [31:0] time_pending_age, spectral_pending_age;
    // Precompute from registered age. The late Lab04 frame-complete/fault
    // decision selects the value; it must not enter a 32-bit carry chain.
    (* keep = "true" *) wire [31:0] time_output_age_inc = time_output_age + 32'd1;
    (* keep = "true" *) wire [31:0] spectral_output_age_inc = spectral_output_age + 32'd1;
    (* keep = "true" *) wire [31:0] time_pending_age_inc = time_pending_age + 32'd1;
    (* keep = "true" *) wire [31:0] spectral_pending_age_inc = spectral_pending_age + 32'd1;
    // R7-B: modulo-2^32 ordering needs equality and the subtraction sign,
    // not the full difference. Four parallel 7/8-bit comparisons plus a
    // group lookahead replace the serial 32-bit subtract / reduce chain.
    // The MSB of (spectral-time) is MSB_xor XOR low31_borrow.
    wire [3:0] id_group_equal, id_group_less;
    assign id_group_equal[0] = spectral_pending_id[6:0] == time_pending_id[6:0];
    assign id_group_equal[1] = spectral_pending_id[14:7] == time_pending_id[14:7];
    assign id_group_equal[2] = spectral_pending_id[22:15] == time_pending_id[22:15];
    assign id_group_equal[3] = spectral_pending_id[30:23] == time_pending_id[30:23];
    assign id_group_less[0] = spectral_pending_id[6:0] < time_pending_id[6:0];
    assign id_group_less[1] = spectral_pending_id[14:7] < time_pending_id[14:7];
    assign id_group_less[2] = spectral_pending_id[22:15] < time_pending_id[22:15];
    assign id_group_less[3] = spectral_pending_id[30:23] < time_pending_id[30:23];
    wire id_low_borrow = id_group_less[3] |
        (id_group_equal[3] & id_group_less[2]) |
        (id_group_equal[3] & id_group_equal[2] & id_group_less[1]) |
        (id_group_equal[3] & id_group_equal[2] & id_group_equal[1] & id_group_less[0]);
    wire id_msb_different = spectral_pending_id[31] ^ time_pending_id[31];
    wire id_low_equal = &id_group_equal;
    wire ids_equal = id_low_equal && !id_msb_different;
    wire id_delta_negative = id_msb_different ^ id_low_borrow;
    wire both_pending = time_pending && spectral_pending;
    wire matching = both_pending && ids_equal;
    wire ambiguous_distance = both_pending && id_low_equal && id_msb_different;
    wire age_limit = source_frame_complete &&
        ((time_pending && time_pending_age >= HALF_SPACE-1) ||
         (spectral_pending && spectral_pending_age >= HALF_SPACE-1) ||
         (time_result_valid && time_output_age >= HALF_SPACE-1) ||
         (spectral_result_valid && spectral_output_age >= HALF_SPACE-1));
    wire stop_now = order_unknown_sticky || ambiguous_distance || age_limit ||
                    acquisition_fault_live;
    wire time_older = both_pending && !ids_equal && !id_delta_negative;
    wire spectral_older = both_pending && id_delta_negative && !ambiguous_distance;

    assign time_result_ready = !time_pending && !stop_now;
    assign spectral_result_ready = !spectral_pending && !stop_now;
    assign time_output_held = time_result_valid && !time_result_ready;
    assign spectral_output_held = spectral_result_valid && !spectral_result_ready;
    assign time_waiting_for_spectral = time_pending && !spectral_pending;
    assign spectral_waiting_for_time = spectral_pending && !time_pending;
    assign combined_result_valid = matching && !stop_now;
    assign combined_frame_id = time_pending_id;
    assign combined_time_payload = time_pending_payload;
    assign combined_spectral_payload = spectral_pending_payload;
    assign combined_valid_mask = {spectral_pending_mask,time_pending_mask};
    assign combined_time_status = time_pending_status;
    assign combined_spectral_status = spectral_pending_status;
    assign combined_numeric_status = numeric_pending_status;
    assign combined_formal_identity = formal_pending_identity;

    always @(posedge clk) begin
        if (reset) begin
            time_pending <= 1'b0; spectral_pending <= 1'b0;
            time_pending_id <= 0; spectral_pending_id <= 0;
            time_pending_payload <= 0; spectral_pending_payload <= 0;
            time_pending_mask <= 0; spectral_pending_mask <= 0;
            time_pending_status <= 0; spectral_pending_status <= 0;
            numeric_pending_status <= 0; formal_pending_identity <= 0;
            time_output_age <= 0; spectral_output_age <= 0;
            time_pending_age <= 0; spectral_pending_age <= 0;
            branch_mismatch_sticky <= 0; order_unknown_sticky <= 0;
            last_mismatch_time_id <= 0; last_mismatch_spectral_id <= 0;
        end else begin
            if (!time_result_valid || (time_result_valid && time_result_ready))
                time_output_age <= 0;
            else if (source_frame_complete && time_output_age < HALF_SPACE)
                time_output_age <= time_output_age + 1'b1;
            if (!spectral_result_valid || (spectral_result_valid && spectral_result_ready))
                spectral_output_age <= 0;
            else if (source_frame_complete && spectral_output_age < HALF_SPACE)
                spectral_output_age <= spectral_output_age + 1'b1;

            if (time_result_valid && time_result_ready) begin
                time_pending <= 1'b1;
                time_pending_id <= time_frame_id;
                time_pending_payload <= time_payload;
                time_pending_mask <= time_valid_mask;
                time_pending_status <= time_status;
                time_pending_age <= source_frame_complete ? time_output_age_inc : time_output_age;
            end else if (time_pending && source_frame_complete && time_pending_age < HALF_SPACE)
                time_pending_age <= time_pending_age_inc;
            if (spectral_result_valid && spectral_result_ready) begin
                spectral_pending <= 1'b1;
                spectral_pending_id <= spectral_frame_id;
                spectral_pending_payload <= spectral_payload;
                spectral_pending_mask <= spectral_valid_mask;
                spectral_pending_status <= spectral_status;
                numeric_pending_status <= spectral_numeric_status;
                formal_pending_identity <= spectral_formal_identity;
                spectral_pending_age <= source_frame_complete ? spectral_output_age_inc : spectral_output_age;
            end else if (spectral_pending && source_frame_complete && spectral_pending_age < HALF_SPACE)
                spectral_pending_age <= spectral_pending_age_inc;

            if (both_pending && !matching) begin
                branch_mismatch_sticky <= 1'b1;
                last_mismatch_time_id <= time_pending_id;
                last_mismatch_spectral_id <= spectral_pending_id;
            end
            if (ambiguous_distance || age_limit) order_unknown_sticky <= 1'b1;
            if (acquisition_fault_live || stop_now) begin
                // Fail closed. No new tuple is accepted until a new epoch.
                time_pending <= 1'b0; spectral_pending <= 1'b0;
            end else if (matching) begin
                time_pending <= 1'b0; spectral_pending <= 1'b0;
            end else if (time_older) begin
                time_pending <= 1'b0;
            end else if (spectral_older) begin
                spectral_pending <= 1'b0;
            end
        end
    end
endmodule
