`timescale 1ns/1ps
// Independent candidate. Does not reset clocks, VTC, AXI controls or DMA.
module lab08_warm_reset_ctrl #(
    parameter integer MIN_RESET_CYCLES = 32
)(
    (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 s_axi_aclk CLK" *)
    (* X_INTERFACE_PARAMETER="ASSOCIATED_BUSIF S_AXI, ASSOCIATED_RESET s_axi_aresetn" *)
    input wire s_axi_aclk,
    (* X_INTERFACE_INFO="xilinx.com:signal:reset:1.0 s_axi_aresetn RST" *)
    (* X_INTERFACE_PARAMETER="POLARITY ACTIVE_LOW" *) input wire s_axi_aresetn,
    (* X_INTERFACE_INFO="xilinx.com:signal:clock:1.0 stream_clk CLK" *)
    (* X_INTERFACE_PARAMETER="ASSOCIATED_RESET stream_resetn" *) input wire stream_clk,
    (* X_INTERFACE_INFO="xilinx.com:signal:reset:1.0 stream_resetn RST" *)
    (* X_INTERFACE_PARAMETER="POLARITY ACTIVE_LOW" *) input wire stream_resetn,
    input wire [11:0] s_axi_awaddr,
    input wire s_axi_awvalid, output wire s_axi_awready,
    input wire [31:0] s_axi_wdata, input wire [3:0] s_axi_wstrb,
    input wire s_axi_wvalid, output wire s_axi_wready,
    output reg [1:0] s_axi_bresp, output reg s_axi_bvalid, input wire s_axi_bready,
    input wire [11:0] s_axi_araddr, input wire s_axi_arvalid,
    output wire s_axi_arready, output reg [31:0] s_axi_rdata,
    output reg [1:0] s_axi_rresp, output reg s_axi_rvalid, input wire s_axi_rready,
    input wire video_locked,
    output wire unpack_resetn
);
    reg request;
    reg aw_saved, w_saved;
    reg [11:0] awaddr;
    reg [31:0] wdata;
    reg [3:0] wstrb;
    (* ASYNC_REG="TRUE" *) reg req_meta, req_sync;
    (* ASYNC_REG="TRUE" *) reg ack_meta, ack_sync;
    (* ASYNC_REG="TRUE" *) reg lock_meta, lock_sync;
    reg active, held_min;
    reg [31:0] hold_count;
    // held_min is itself registered in stream_clk. The state machine keeps
    // held_min -> active invariant; avoid combinational logic before CDC.
    wire acknowledged = held_min;
    assign unpack_resetn = stream_resetn && !active;
    assign s_axi_awready = s_axi_aresetn && !aw_saved && !s_axi_bvalid;
    assign s_axi_wready = s_axi_aresetn && !w_saved && !s_axi_bvalid;
    assign s_axi_arready = s_axi_aresetn && !s_axi_rvalid;

    // Each destination releases through its own clock. Source request is held
    // until software has observed ACK; the ACK is never a sampled pulse.
    always @(posedge stream_clk) begin
        if (!stream_resetn) begin
            req_meta <= 0; req_sync <= 0;
            active <= 0; held_min <= 0; hold_count <= 0;
        end else begin
            req_meta <= request; req_sync <= req_meta;
            if (!active) begin
                held_min <= 0; hold_count <= 0;
                if (req_sync) active <= 1;
            end else if (!held_min) begin
                if (hold_count == MIN_RESET_CYCLES-1) held_min <= 1;
                else hold_count <= hold_count + 1;
            end else if (!req_sync) begin
                active <= 0; held_min <= 0; hold_count <= 0;
            end
        end
    end
    always @(posedge s_axi_aclk) begin
        if (!s_axi_aresetn) begin
            ack_meta <= 0; ack_sync <= 0; lock_meta <= 0; lock_sync <= 0;
            request <= 0; aw_saved <= 0; w_saved <= 0;
            awaddr <= 0; wdata <= 0; wstrb <= 0;
            s_axi_bvalid <= 0; s_axi_bresp <= 0;
            s_axi_rvalid <= 0; s_axi_rresp <= 0; s_axi_rdata <= 0;
        end else begin
            ack_meta <= acknowledged; ack_sync <= ack_meta;
            lock_meta <= video_locked; lock_sync <= lock_meta;
            if (s_axi_awvalid && s_axi_awready) begin aw_saved<=1; awaddr<=s_axi_awaddr; end
            if (s_axi_wvalid && s_axi_wready) begin w_saved<=1; wdata<=s_axi_wdata; wstrb<=s_axi_wstrb; end
            if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 0;
            if (aw_saved && w_saved && !s_axi_bvalid) begin
                aw_saved<=0; w_saved<=0; s_axi_bvalid<=1;
                if (awaddr == 12'h004) begin
                    s_axi_bresp<=0;
                    if (wstrb[0]) request<=wdata[0];
                end else s_axi_bresp<=2'b10; // SLVERR, including RO writes
            end
            if (s_axi_rvalid && s_axi_rready) s_axi_rvalid<=0;
            if (s_axi_arvalid && s_axi_arready) begin
                s_axi_rvalid<=1; s_axi_rresp<=0;
                case (s_axi_araddr)
                    12'h000: s_axi_rdata<=32'h57520201;
                    12'h004: s_axi_rdata<={31'b0,request};
                    12'h008: s_axi_rdata<={30'b0,lock_sync,ack_sync};
                    12'h00c: s_axi_rdata<=MIN_RESET_CYCLES;
                    default: begin s_axi_rdata<=0; s_axi_rresp<=2'b10; end
                endcase
            end
        end
    end
endmodule
