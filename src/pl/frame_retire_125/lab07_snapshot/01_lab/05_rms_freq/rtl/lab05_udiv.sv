`timescale 1ns/1ps
// Unsigned restoring division: fixed 62 iterations, including divisor zero.
// Zero divisor returns quotient=0 and divide_by_zero=1, with identical latency.
module lab05_udiv (
    input wire clk, reset, start,
    input wire [61:0] numerator,
    input wire [41:0] denominator,
    output reg busy, done, divide_by_zero,
    output reg [61:0] quotient
);
    reg [61:0] operand, partial_quotient;
    reg [41:0] divisor;
    reg [42:0] remainder;
    reg [5:0] count;
    wire [42:0] shifted = {remainder[41:0], operand[61]};
    wire take_bit = shifted >= {1'b0, divisor};
    wire [42:0] next_remainder = take_bit ? shifted - {1'b0, divisor} : shifted;
    wire [61:0] next_quotient = {partial_quotient[60:0], take_bit};
    always @(posedge clk) begin
        if (reset) begin
            busy <= 0; done <= 0; divide_by_zero <= 0; quotient <= 0;
            operand <= 0; divisor <= 0; remainder <= 0;
            partial_quotient <= 0; count <= 0;
        end else begin
            done <= 0;
            if (start && !busy) begin
                busy <= 1; operand <= numerator; divisor <= denominator;
                divide_by_zero <= denominator == 42'd0;
                remainder <= 0; partial_quotient <= 0; count <= 0;
            end else if (busy) begin
                operand <= {operand[60:0], 1'b0};
                remainder <= next_remainder; partial_quotient <= next_quotient;
                if (count == 6'd61) begin
                    quotient <= divide_by_zero ? 62'd0 : next_quotient;
                    busy <= 0; done <= 1;
                end else count <= count + 6'd1;
            end
        end
    end
endmodule
