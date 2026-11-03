`timescale 1ns / 1ps
// Epoch = FPGA INIT/reconfiguration. Deliberately has no dynamic reset.
module lab04_raw_transport #(
    parameter integer CONVERSION_PERIOD = 12500,
    parameter integer SNAPSHOT_FRAME_COUNT = 147
) (
    input wire clk, input wire [15:0] sample_ch1, sample_ch2,
    input wire dual_sample_valid, ad_convst, busy_timeout, frstdata_mismatch,
    output wire sample_write_commit, raw_sample_valid, raw_frame_valid,
    output wire debug_sample_valid, output wire [10:0] debug_sample_index,
    output wire [31:0] debug_frame_id, debug_sequence_id,
    output wire [15:0] debug_ch1, debug_ch2, output wire debug_frame_done,
    output wire acquisition_fault, output wire source_error_sticky,
    output reg sequence_error_sticky = 0, buffer_overrun_sticky = 0,
    output reg busy_timeout_sticky = 0, frstdata_mismatch_sticky = 0,
    output reg readback_error_sticky = 0,
    output reg [31:0] samples_received = 0, samples_written = 0, samples_read = 0,
    output reg [31:0] frames_completed = 0, frames_read = 0,
    output reg [1:0] bank_a_state = 0, bank_b_state = 0,
    output reg current_bank = 0, output reg [10:0] raw_sample_index = 0,
    output reg writer_active = 0,
    output reg [31:0] sequence_id = 0, raw_frame_id = 0,
    output reg [31:0] fault_sequence_id = 0, fault_frame_id = 0,
    output reg fault_bank = 0, output reg [10:0] fault_index = 0,
    output reg [7:0] fault_code = 0,
    output reg snapshot_valid = 0,
    output reg [31:0] snapshot_samples_received = 0, snapshot_samples_written = 0,
    output reg [31:0] snapshot_samples_read = 0, snapshot_frames_completed = 0,
    output reg [31:0] snapshot_frames_read = 0,
    output reg snapshot_current_bank = 0, snapshot_writer_active = 0,
    output reg [10:0] snapshot_current_index = 0,
    output reg [6:0] snapshot_error_flags = 0
);
    localparam [1:0] EMPTY=0, FILLING=1, READY=2, READING=3;
    localparam [2:0] IDLE=0, STREAM=1, DRAIN=2, RELEASE_BANK=3, ERROR=4;
    reg fault_latched = 0;
    wire source_error_now, pair_eligible;
    wire [3:0] source_code;
    wire conversion_seen;
    wire [1:0] conversion_pair_count;
    wire [31:0] interval_age;
    lab04_source_monitor #(.CONVERSION_PERIOD(CONVERSION_PERIOD)) u_source (
        .clk(clk), .ad_convst(ad_convst), .dual_sample_valid(dual_sample_valid),
        .freeze(fault_latched), .pair_eligible(pair_eligible),
        .error_now(source_error_now), .source_error_sticky(source_error_sticky),
        .event_code(source_code), .conversion_seen(conversion_seen),
        .current_conversion_pair_count(conversion_pair_count), .interval_age(interval_age)
    );
    reg [31:0] expected_write_sequence = 0;
    wire legal_producer = dual_sample_valid && pair_eligible;
    wire overrun_now = !fault_latched && legal_producer && !writer_active;
    wire write_sequence_bad = !fault_latched && legal_producer && writer_active &&
                              sequence_id != expected_write_sequence;
    wire fault_pre = fault_latched || source_error_now || overrun_now ||
                     write_sequence_bad || busy_timeout || frstdata_mismatch;

    reg [31:0] bank_a_frame_id = 0, bank_b_frame_id = 0;
    reg [31:0] bank_a_start_sequence = 0, bank_b_start_sequence = 0;
    reg [31:0] bank_a_end_sequence = 0, bank_b_end_sequence = 0;
    reg [31:0] filling_start_sequence = 0;
    reg next_writer_bank = 0;
    reg [2:0] reader_state = IDLE;
    reg reader_bank = 0, next_reader_bank = 0;
    reg [10:0] request_index = 0;
    reg [31:0] reader_frame_id = 0, reader_start_sequence = 0, reader_end_sequence = 0;
    wire [63:0] bank_a_data, bank_b_data;
    wire read_request = reader_state == STREAM && !acquisition_fault;
    reg read_valid_q = 0, read_bank_q = 0;
    reg [10:0] read_index_q = 0;
    reg [31:0] read_frame_q = 0;
    wire [63:0] bram_mux_record = read_bank_q ? bank_b_data : bank_a_data;
    // E0 request -> E1 post-mux fabric register -> E2 validated consume.
    // The full record and its 45 metadata bits cross this boundary together.
    reg [63:0] read_record_pipe = 0;
    reg read_valid_pipe = 0, read_bank_pipe = 0;
    reg [10:0] read_index_pipe = 0;
    reg [31:0] read_frame_pipe = 0;
    reg [31:0] expected_debug_sequence = 0, expected_debug_frame = 0;
    reg [10:0] expected_debug_index = 0;
    wire candidate_valid = read_valid_pipe && !fault_pre;
    wire read_sequence_bad = candidate_valid && read_record_pipe[63:32] != expected_debug_sequence;
    wire read_shape_bad = candidate_valid &&
        (read_index_pipe != expected_debug_index || read_frame_pipe != expected_debug_frame ||
         (read_index_pipe == 0 && read_record_pipe[63:32] != reader_start_sequence) ||
         (read_index_pipe == 2047 && read_record_pipe[63:32] != reader_end_sequence));
    wire readback_bad = read_sequence_bad || read_shape_bad;
    wire fault_now = fault_pre || readback_bad;
    assign acquisition_fault = fault_now;
    assign raw_sample_valid = dual_sample_valid;
    assign sample_write_commit = legal_producer && writer_active && !fault_now;
    reg raw_frame_pulse = 0;
    assign raw_frame_valid = raw_frame_pulse && !fault_now;
    assign debug_sample_valid = candidate_valid && !readback_bad;
    assign debug_sample_index = read_index_pipe;
    assign debug_frame_id = read_frame_pipe;
    assign debug_sequence_id = read_record_pipe[63:32];
    assign debug_ch1 = read_record_pipe[31:16];
    assign debug_ch2 = read_record_pipe[15:0];
    assign debug_frame_done = debug_sample_valid && read_index_pipe == 2047;
    wire last_commit = sample_write_commit && raw_sample_index == 2047;
    wire other_empty = current_bank ? bank_a_state == EMPTY : bank_b_state == EMPTY;
    wire [63:0] producer_record = {sequence_id, sample_ch1, sample_ch2};
    lab04_bram_bank u_bank_a (.clk(clk),
        .write_en(sample_write_commit && !current_bank), .write_addr(raw_sample_index),
        .write_data(producer_record), .read_en(read_request && !reader_bank),
        .read_addr(request_index), .read_data(bank_a_data));
    lab04_bram_bank u_bank_b (.clk(clk),
        .write_en(sample_write_commit && current_bank), .write_addr(raw_sample_index),
        .write_data(producer_record), .read_en(read_request && reader_bank),
        .read_addr(request_index), .read_data(bank_b_data));

    // E0: synchronous BRAM return and matching request metadata.
    always @(posedge clk) begin
        read_valid_q <= read_request;
        if (read_request) begin
            read_index_q <= request_index;
            read_frame_q <= reader_frame_id;
            read_bank_q <= reader_bank;
        end
        // E1: valid explicitly clears for every bubble; no stale valid repeat.
        read_valid_pipe <= read_valid_q;
        if (read_valid_q) begin
            read_record_pipe <= bram_mux_record;
            read_index_pipe <= read_index_q;
            read_frame_pipe <= read_frame_q;
            read_bank_pipe <= read_bank_q;
        end
    end
    always @(posedge clk) begin
        raw_frame_pulse <= 0;
        // Producer accounting NEVER depends on storage success or fault.
        if (dual_sample_valid) begin
            samples_received <= samples_received + 1'b1;
            sequence_id <= sequence_id + 1'b1;
        end
        if (!fault_latched && fault_now) begin
            fault_latched <= 1;
            fault_sequence_id <= readback_bad ? read_record_pipe[63:32] : sequence_id;
            fault_frame_id <= readback_bad ? read_frame_pipe : raw_frame_id;
            fault_bank <= readback_bad ? read_bank_pipe : current_bank;
            fault_index <= readback_bad ? read_index_pipe : raw_sample_index;
            if (busy_timeout) fault_code <= 8'h20;
            else if (frstdata_mismatch) fault_code <= 8'h21;
            else if (source_error_now) fault_code <= {4'd0,source_code};
            else if (overrun_now) fault_code <= 8'h10;
            else if (write_sequence_bad) fault_code <= 8'h11;
            else fault_code <= 8'h30;
            busy_timeout_sticky <= busy_timeout;
            frstdata_mismatch_sticky <= frstdata_mismatch;
            buffer_overrun_sticky <= overrun_now;
            sequence_error_sticky <= write_sequence_bad || read_sequence_bad;
            readback_error_sticky <= readback_bad;
            reader_state <= ERROR;
        end
        if (!fault_now) begin
            // Proactive allocation reads OLD bank states. RELEASE_BANK below
            // cannot be bypassed by writer acquisition in this same edge.
            if (!writer_active) begin
                if ((!next_writer_bank && bank_a_state == EMPTY) || bank_b_state != EMPTY) begin
                    if (bank_a_state == EMPTY) begin
                        bank_a_state <= FILLING; current_bank <= 0;
                        writer_active <= 1; raw_sample_index <= 0;
                    end
                end else if (bank_b_state == EMPTY) begin
                    bank_b_state <= FILLING; current_bank <= 1;
                    writer_active <= 1; raw_sample_index <= 0;
                end
            end
            if (sample_write_commit) begin
                samples_written <= samples_written + 1'b1;
                expected_write_sequence <= expected_write_sequence + 1'b1;
                if (raw_sample_index == 0) filling_start_sequence <= sequence_id;
                if (last_commit) begin
                    raw_frame_pulse <= 1;
                    frames_completed <= frames_completed + 1'b1;
                    raw_frame_id <= raw_frame_id + 1'b1;
                    if (!current_bank) begin
                        bank_a_state <= READY; bank_a_frame_id <= raw_frame_id;
                        bank_a_start_sequence <= filling_start_sequence;
                        bank_a_end_sequence <= sequence_id;
                    end else begin
                        bank_b_state <= READY; bank_b_frame_id <= raw_frame_id;
                        bank_b_start_sequence <= filling_start_sequence;
                        bank_b_end_sequence <= sequence_id;
                    end
                    next_writer_bank <= !current_bank;
                    raw_sample_index <= 0;
                    writer_active <= other_empty;
                    if (other_empty) begin
                        current_bank <= !current_bank;
                        if (current_bank) bank_a_state <= FILLING;
                        else bank_b_state <= FILLING;
                    end
                end else raw_sample_index <= raw_sample_index + 1'b1;
            end
            case (reader_state)
                IDLE: begin
                    if (bank_a_state == READY || bank_b_state == READY) begin
                        // Alternation is completion order even across frame-ID wrap.
                        if (bank_a_state == READY && (bank_b_state != READY || !next_reader_bank)) begin
                            reader_bank <= 0; bank_a_state <= READING;
                            reader_frame_id <= bank_a_frame_id;
                            reader_start_sequence <= bank_a_start_sequence;
                            reader_end_sequence <= bank_a_end_sequence;
                        end else begin
                            reader_bank <= 1; bank_b_state <= READING;
                            reader_frame_id <= bank_b_frame_id;
                            reader_start_sequence <= bank_b_start_sequence;
                            reader_end_sequence <= bank_b_end_sequence;
                        end
                        request_index <= 0; reader_state <= STREAM;
                    end
                end
                STREAM: begin
                    if (read_request) begin
                        if (request_index == 2047) reader_state <= DRAIN;
                        else request_index <= request_index + 1'b1;
                    end
                end
                DRAIN: if (debug_frame_done) reader_state <= RELEASE_BANK;
                RELEASE_BANK: begin
                    if (reader_bank) bank_b_state <= EMPTY;
                    else bank_a_state <= EMPTY;
                    next_reader_bank <= !reader_bank;
                    reader_state <= IDLE;
                end
                default: reader_state <= ERROR;
            endcase
            if (debug_sample_valid) begin
                samples_read <= samples_read + 1'b1;
                expected_debug_sequence <= expected_debug_sequence + 1'b1;
                if (debug_frame_done) begin
                    frames_read <= frames_read + 1'b1;
                    expected_debug_frame <= expected_debug_frame + 1'b1;
                    expected_debug_index <= 0;
                end else expected_debug_index <= expected_debug_index + 1'b1;
            end
            // Atomic POST-EVENT counter image, including a coincident producer
            // event/write/frame completion. Snapshot is observation only.
            if (!snapshot_valid && debug_frame_done && frames_read == SNAPSHOT_FRAME_COUNT-1) begin
                snapshot_valid <= 1;
                snapshot_samples_received <= samples_received + dual_sample_valid;
                snapshot_samples_written <= samples_written + sample_write_commit;
                snapshot_samples_read <= samples_read + 1'b1;
                snapshot_frames_completed <= frames_completed + last_commit;
                snapshot_frames_read <= frames_read + 1'b1;
                snapshot_current_bank <= last_commit && other_empty ? !current_bank : current_bank;
                snapshot_current_index <= sample_write_commit ? (last_commit ? 0 : raw_sample_index + 1'b1) : raw_sample_index;
                snapshot_writer_active <= last_commit ? other_empty : writer_active;
                snapshot_error_flags <= {acquisition_fault, readback_error_sticky,
                    frstdata_mismatch_sticky, busy_timeout_sticky, buffer_overrun_sticky,
                    sequence_error_sticky, source_error_sticky};
            end
        end
    end
endmodule
