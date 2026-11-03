`timescale 1ns/1ps
// Mirror of the Lab04 write-accepted stream for a future mapped-BRAM reader.
// There is one published PS descriptor and at most one completed waiting bank.
module raw_frame_bank_manager (
    input wire clk,
    input wire reset,
    input wire sample_valid,
    input wire [10:0] sample_index,
    input wire [31:0] sample_frame_id,
    input wire signed [15:0] ch1_code,
    input wire signed [15:0] ch2_code,
    input wire frame_abort,
    input wire raw_ack_valid,
    input wire raw_ack_bank_id,
    input wire [31:0] raw_ack_token,
    input wire raw_read_en,
    input wire raw_read_bank_id,
    input wire [10:0] raw_read_index,
    output reg [31:0] raw_read_data,
    output reg raw_read_valid,
    output wire raw_frame_valid,
    output wire raw_bank_id,
    output wire [31:0] raw_frame_id,
    output wire [7:0] raw_status,
    output reg [31:0] raw_owner_token,
    output reg raw_drop_sticky,
    output reg [31:0] raw_drop_count,
    output reg raw_protocol_sticky,
    output reg raw_ack_error_sticky,
    output reg raw_token_exhausted_sticky,
    output wire [7:0] raw_bank_states
);
    localparam [1:0] EMPTY=2'd0, FILLING=2'd1,
                     COMPLETE_PENDING=2'd2, PS_OWNED=2'd3;
    (* ram_style="block" *) reg [31:0] mem [0:4095];
    reg [1:0] bank_state [0:1];
    reg [31:0] bank_frame_id [0:1];
    reg [7:0] bank_status [0:1];
    reg fill_bank;
    reg [31:0] fill_frame_id;
    reg [10:0] expected_index;
    reg skip_frame;
    reg [31:0] skipped_frame_id;
    reg owner_valid, owner_bank;
    reg [31:0] next_owner_token;
    wire has_empty = bank_state[0]==EMPTY || bank_state[1]==EMPTY;
    wire free_bank = bank_state[0]!=EMPTY;
    wire filling = bank_state[fill_bank]==FILLING;
    wire start_write = !reset && sample_valid && sample_index==11'd0 &&
                       !frame_abort && !filling && has_empty;
    wire continue_write = !reset && sample_valid && sample_index!=11'd0 &&
                          !frame_abort && filling && !skip_frame &&
                          sample_frame_id==fill_frame_id &&
                          sample_index==expected_index;
    wire write_bank = filling ? fill_bank : free_bank;
    wire read_legal = raw_read_en && owner_valid &&
                      raw_read_bank_id==owner_bank;
    wire ack_match = raw_ack_valid && owner_valid &&
                     raw_ack_bank_id==owner_bank &&
                     raw_ack_token==raw_owner_token;

    assign raw_frame_valid = owner_valid;
    assign raw_bank_id = owner_bank;
    assign raw_frame_id = bank_frame_id[owner_bank];
    assign raw_status = bank_status[owner_bank];
    assign raw_bank_states = {2'b00,bank_state[1],2'b00,bank_state[0]};

    // Memory contains no reset tree; only owned bank data is readable.
    always @(posedge clk) begin
        if (start_write || continue_write)
            mem[{write_bank,sample_index}] <= {ch2_code,ch1_code};
        raw_read_valid <= read_legal && !reset;
        if (read_legal) raw_read_data <= mem[{raw_read_bank_id,raw_read_index}];
    end

    always @(posedge clk) begin
        if (reset) begin
            bank_state[0] <= EMPTY; bank_state[1] <= EMPTY;
            bank_frame_id[0] <= 0; bank_frame_id[1] <= 0;
            bank_status[0] <= 0; bank_status[1] <= 0;
            fill_bank <= 0; fill_frame_id <= 0; expected_index <= 0;
            skip_frame <= 0; skipped_frame_id <= 0;
            owner_valid <= 0; owner_bank <= 0;
            next_owner_token <= 0; raw_owner_token <= 0;
            raw_drop_sticky <= 0; raw_drop_count <= 0;
            raw_protocol_sticky <= 0; raw_ack_error_sticky <= 0;
            raw_token_exhausted_sticky <= 0;
        end else begin
            // Priority 1: integrity abort. It never revokes PS ownership.
            if (frame_abort) begin
                if (filling) bank_state[fill_bank] <= EMPTY;
                skip_frame <= 0;
                expected_index <= 0;
            end else if (sample_valid) begin
                if (sample_index==11'd0) begin
                    // Allocation uses only bank states from before this edge.
                    skip_frame <= 0;
                    if (filling) begin
                        bank_state[fill_bank] <= EMPTY;
                        raw_protocol_sticky <= 1;
                    end else if (!has_empty) begin
                        skip_frame <= 1;
                        skipped_frame_id <= sample_frame_id;
                        raw_drop_sticky <= 1;
                        raw_drop_count <= raw_drop_count + 1'b1;
                    end else begin
                        bank_state[free_bank] <= FILLING;
                        bank_frame_id[free_bank] <= sample_frame_id;
                        bank_status[free_bank] <= 8'h01;
                        fill_bank <= free_bank;
                        fill_frame_id <= sample_frame_id;
                        expected_index <= 11'd1;
                    end
                end else if (filling && !skip_frame) begin
                    if (sample_frame_id != fill_frame_id ||
                        sample_index != expected_index) begin
                        bank_state[fill_bank] <= EMPTY;
                        expected_index <= 0;
                        raw_protocol_sticky <= 1;
                    end else if (sample_index==11'd2047) begin
                        // Priority 2: the completed bank waits for publication.
                        bank_state[fill_bank] <= COMPLETE_PENDING;
                        bank_frame_id[fill_bank] <= fill_frame_id;
                        expected_index <= 0;
                    end else expected_index <= expected_index + 1'b1;
                end else if (skip_frame && sample_frame_id==skipped_frame_id) begin
                    if (sample_index==11'd2047) skip_frame <= 0;
                end else if (!skip_frame) raw_protocol_sticky <= 1;
            end

            // Priority 3: ack applies only to the PRE-edge descriptor.
            if (raw_ack_valid && !ack_match) raw_ack_error_sticky <= 1;
            if (ack_match) begin
                bank_state[owner_bank] <= EMPTY;
                owner_valid <= 0;
            end

            // Priority 4: promote an already-completed bank only if there was
            // no owner before this edge. A coincident completion is not seen.
            if (!owner_valid && !frame_abort &&
                (bank_state[0]==COMPLETE_PENDING ||
                 bank_state[1]==COMPLETE_PENDING) &&
                next_owner_token==32'hffff_ffff)
                raw_token_exhausted_sticky <= 1'b1;
            if (!owner_valid && !frame_abort && !raw_token_exhausted_sticky &&
                next_owner_token!=32'hffff_ffff) begin
                if (bank_state[0]==COMPLETE_PENDING) begin
                    bank_state[0] <= PS_OWNED;
                    owner_bank <= 0; owner_valid <= 1;
                    next_owner_token <= next_owner_token + 1'b1;
                    raw_owner_token <= next_owner_token + 1'b1;
                end else if (bank_state[1]==COMPLETE_PENDING) begin
                    bank_state[1] <= PS_OWNED;
                    owner_bank <= 1; owner_valid <= 1;
                    next_owner_token <= next_owner_token + 1'b1;
                    raw_owner_token <= next_owner_token + 1'b1;
                end
            end
        end
    end
endmodule
