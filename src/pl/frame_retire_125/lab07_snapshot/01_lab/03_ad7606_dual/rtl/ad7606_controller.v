`timescale 1ns / 1ps

// AD7606 16-bit parallel reader. All cycle counts refer to clk_125mhz edges.
// The FPGA register INIT values hold the interface inactive while it configures.
module ad7606_controller #(
    parameter integer SAMPLE_PERIOD_CYCLES = 12500,    // 100 us / 10 kSPS
    parameter integer RESET_CYCLES         = 250,      // 2 us; datasheet min 50 ns
    parameter integer STARTUP_CYCLES       = 3750000,  // 30 ms, internal-reference wake-up margin
    parameter integer CONVST_CYCLES        = 125,      // 1 us; min high/low 25 ns
    parameter integer BUSY_TIMEOUT_CYCLES  = 2500,     // 20 us for each BUSY edge
    parameter integer CS_SETUP_CYCLES      = 8,        // 64 ns
    parameter integer RD_LOW_CYCLES        = 16,       // 128 ns; min 32 ns at low VDRIVE
    parameter integer DATA_SAMPLE_CYCLES   = 12,       // 96 ns after RD falling; access max 32 ns
    parameter integer RD_HIGH_CYCLES       = 8         // 64 ns; min 15 ns
) (
    input  wire        clk_125mhz,
    input  wire [15:0] ad_data,
    input  wire        ad_busy,
    input  wire        ad_frstdata,
    output reg         ad_convst = 1'b0,
    output reg         ad_reset = 1'b1,
    output reg         ad_cs_n = 1'b1,
    output reg         ad_rd_n = 1'b1,
    output reg  [15:0] sample_ch1 = 16'h0000,
    output reg  [15:0] sample_ch2 = 16'h0000,
    output reg  [15:0] ch1_hold = 16'h0000,
    output reg         ch1_hold_valid = 1'b0,
    output reg         dual_sample_valid = 1'b0,
    output reg         sample_valid = 1'b0,
    output reg         frame_valid = 1'b0,
    output reg  [2:0]  channel_index = 3'd0,
    output wire        valid_capture_event,
    output wire        busy_sync,
    output reg         busy_timeout = 1'b0,
    output reg         frstdata_mismatch = 1'b0
);
    localparam [3:0] ST_RESET         = 4'd0;
    localparam [3:0] ST_STARTUP_WAIT  = 4'd1;
    localparam [3:0] ST_IDLE          = 4'd2;
    localparam [3:0] ST_CONVST        = 4'd3;
    localparam [3:0] ST_WAIT_BUSY_HI  = 4'd4;
    localparam [3:0] ST_WAIT_BUSY_LO  = 4'd5;
    localparam [3:0] ST_CS_SETUP      = 4'd6;
    localparam [3:0] ST_RD_LOW        = 4'd7;
    localparam [3:0] ST_RD_HIGH       = 4'd8;
    localparam [3:0] ST_FRAME_DONE    = 4'd9;
    localparam [3:0] ST_ERROR         = 4'd10;

    reg [3:0]  state = ST_RESET;
    reg [31:0] phase_count = 32'd0;
    reg [31:0] period_count = 32'd0;
    (* ASYNC_REG = "TRUE" *) reg busy_meta = 1'b0;
    (* ASYNC_REG = "TRUE" *) reg busy_sync_reg = 1'b0;
    assign busy_sync = busy_sync_reg;
    // The same DB/FRSTDATA capture edge used by frozen Lab02.
    assign valid_capture_event = (state == ST_RD_LOW) &&
                                 (phase_count == DATA_SAMPLE_CYCLES - 1);

    // BUSY is asynchronous. DB and FRSTDATA are sampled together only after
    // the external parallel-read access time has elapsed; they are not 2FF CDCs.
    always @(posedge clk_125mhz) begin
        busy_meta     <= ad_busy;
        busy_sync_reg <= busy_meta;
    end

    always @(posedge clk_125mhz) begin
        sample_valid <= 1'b0;
        // A pair is committed atomically at V2 capture; old output values are
        // never a new sample without this one-clock pulse.
        dual_sample_valid <= 1'b0;
        // frame_valid denotes completion of this conversion's V1..V8 reads.
        frame_valid  <= 1'b0;
        if (period_count < SAMPLE_PERIOD_CYCLES)
            period_count <= period_count + 1'b1;

        case (state)
            ST_RESET: begin
                ch1_hold_valid <= 1'b0;
                if (phase_count == RESET_CYCLES - 1) begin
                    ad_reset   <= 1'b0;
                    phase_count <= 32'd0;
                    state      <= ST_STARTUP_WAIT;
                end else phase_count <= phase_count + 1'b1;
            end

            ST_STARTUP_WAIT: begin
                ch1_hold_valid <= 1'b0;
                if (phase_count == STARTUP_CYCLES - 1) begin
                    phase_count  <= 32'd0;
                    period_count <= SAMPLE_PERIOD_CYCLES - 1;
                    state        <= ST_IDLE;
                end else phase_count <= phase_count + 1'b1;
            end

            ST_IDLE: begin
                if (period_count >= SAMPLE_PERIOD_CYCLES - 1) begin
                    ch1_hold_valid <= 1'b0;
                    period_count <= 32'd0;
                    phase_count  <= 32'd0;
                    channel_index <= 3'd0;
                    ad_convst    <= 1'b1;
                    state        <= ST_CONVST;
                end
            end

            ST_CONVST: begin
                if (phase_count == CONVST_CYCLES - 1) begin
                    ad_convst   <= 1'b0;
                    phase_count <= 32'd0;
                    state       <= ST_WAIT_BUSY_HI;
                end else phase_count <= phase_count + 1'b1;
            end

            ST_WAIT_BUSY_HI: begin
                if (busy_sync_reg) begin
                    phase_count <= 32'd0;
                    state       <= ST_WAIT_BUSY_LO;
                end else if (phase_count == BUSY_TIMEOUT_CYCLES - 1) begin
                    busy_timeout <= 1'b1;
                    ch1_hold_valid <= 1'b0;
                    state <= ST_ERROR;
                end else phase_count <= phase_count + 1'b1;
            end

            ST_WAIT_BUSY_LO: begin
                if (!busy_sync_reg) begin
                    ad_cs_n     <= 1'b0;
                    phase_count <= 32'd0;
                    state       <= ST_CS_SETUP;
                end else if (phase_count == BUSY_TIMEOUT_CYCLES - 1) begin
                    busy_timeout <= 1'b1;
                    ch1_hold_valid <= 1'b0;
                    state <= ST_ERROR;
                end else phase_count <= phase_count + 1'b1;
            end

            ST_CS_SETUP: begin
                if (phase_count == CS_SETUP_CYCLES - 1) begin
                    ad_rd_n     <= 1'b0;
                    phase_count <= 32'd0;
                    state       <= ST_RD_LOW;
                end else phase_count <= phase_count + 1'b1;
            end

            ST_RD_LOW: begin
                if (valid_capture_event) begin
                    if (ad_frstdata != (channel_index == 3'd0))
                        frstdata_mismatch <= 1'b1;
                    if (channel_index == 3'd0) begin
                        ch1_hold <= ad_data;
                        ch1_hold_valid <= 1'b1;
                    end else if (channel_index == 3'd1) begin
                        if (ch1_hold_valid) begin
                            sample_ch1 <= ch1_hold;
                            sample_ch2 <= ad_data;
                            sample_valid <= 1'b1; // legacy alias of pair valid
                            dual_sample_valid <= 1'b1;
                        end
                        ch1_hold_valid <= 1'b0;
                    end
                end
                if (phase_count == RD_LOW_CYCLES - 1) begin
                    ad_rd_n     <= 1'b1;
                    phase_count <= 32'd0;
                    state       <= ST_RD_HIGH;
                end else phase_count <= phase_count + 1'b1;
            end

            ST_RD_HIGH: begin
                if (phase_count == RD_HIGH_CYCLES - 1) begin
                    phase_count <= 32'd0;
                    if (channel_index == 3'd7) begin
                        ad_cs_n <= 1'b1;
                        state   <= ST_FRAME_DONE;
                    end else begin
                        channel_index <= channel_index + 1'b1;
                        ad_rd_n       <= 1'b0;
                        state         <= ST_RD_LOW;
                    end
                end else phase_count <= phase_count + 1'b1;
            end

            ST_FRAME_DONE: begin
                frame_valid <= 1'b1;
                state       <= ST_IDLE;
            end

            ST_ERROR: begin
                ch1_hold_valid <= 1'b0;
                ad_convst <= 1'b0;
                ad_cs_n   <= 1'b1;
                ad_rd_n   <= 1'b1;
            end

            default: begin
                ch1_hold_valid <= 1'b0;
                state <= ST_ERROR;
            end
        endcase
    end
endmodule
