`timescale 1ns / 1ps
// Simple dual-port synchronous BRAM. Request sampled at edge T produces data
// after T (one synchronous read stage, L=1). No reset/clear of stored records.
module lab04_bram_bank (
    input wire clk, input wire write_en, input wire [10:0] write_addr,
    input wire [63:0] write_data, input wire read_en,
    input wire [10:0] read_addr, output reg [63:0] read_data
);
    (* ram_style = "block" *) reg [63:0] mem [0:2047];
    always @(posedge clk) begin
        if (write_en) mem[write_addr] <= write_data;
        if (read_en) read_data <= mem[read_addr];
    end
endmodule
