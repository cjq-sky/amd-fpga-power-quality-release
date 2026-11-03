`timescale 1ns/1ps
// Restoring radix-4 floor sqrt. start accepted only when !busy.
// A 32-bit radicand takes exactly 16 clocks after the accepting edge.
module lab05_isqrt (
    input wire clk, reset, start,
    input wire [31:0] radicand,
    output reg busy, done,
    output reg [15:0] root
);
    reg [31:0] operand;
    reg [17:0] remainder;
    reg [15:0] partial_root;
    reg [4:0] count;
    wire [17:0] shifted = {remainder[15:0], operand[31:30]};
    wire [17:0] trial = {partial_root, 2'b01};
    wire take_bit = shifted >= trial;
    wire [17:0] next_remainder = take_bit ? shifted - trial : shifted;
    wire [15:0] next_root = {partial_root[14:0], take_bit};
    always @(posedge clk) begin
        if (reset) begin
            busy <= 0; done <= 0; root <= 0; operand <= 0;
            remainder <= 0; partial_root <= 0; count <= 0;
        end else begin
            done <= 0;
            if (start && !busy) begin
                busy <= 1; operand <= radicand; remainder <= 0;
                partial_root <= 0; count <= 0;
            end else if (busy) begin
                operand <= {operand[29:0], 2'b00};
                remainder <= next_remainder; partial_root <= next_root;
                if (count == 5'd15) begin
                    root <= next_root; busy <= 0; done <= 1;
                end else count <= count + 5'd1;
            end
        end
    end
endmodule
