`timescale 1ns / 1ps
module lab04_source_monitor #(
    parameter integer CONVERSION_PERIOD = 12500
) (
    input wire clk, input wire ad_convst, input wire dual_sample_valid,
    input wire freeze, output wire pair_eligible, output wire error_now,
    output reg source_error_sticky = 0, output wire [3:0] event_code,
    output reg conversion_seen = 0,
    output reg [1:0] current_conversion_pair_count = 0,
    output reg [31:0] interval_age = 0
);
    reg convst_d = 0;
    wire rising = ad_convst && !convst_d;
    wire wrong_interval = rising && conversion_seen &&
                          interval_age != CONVERSION_PERIOD-1;
    wire missing = rising && conversion_seen && current_conversion_pair_count != 1;
    wire timeout = !rising && conversion_seen && interval_age >= CONVERSION_PERIOD-1;
    // A coincident rising-edge pair belongs to the NEW interval. The old
    // interval is checked independently before its count is cleared.
    wire unexpected = dual_sample_valid && !conversion_seen && !rising;
    wire multiple = dual_sample_valid && !rising &&
                    conversion_seen && current_conversion_pair_count != 0;
    assign error_now = !freeze && (wrong_interval || missing || timeout || unexpected || multiple);
    assign event_code = unexpected ? 1 : multiple ? 2 : wrong_interval ? 3 : missing ? 4 : 5;
    assign pair_eligible = (conversion_seen || rising) &&
                           (rising || current_conversion_pair_count == 0) && !error_now;
    always @(posedge clk) begin
        convst_d <= ad_convst;
        if (!freeze) begin
            if (error_now) begin
                source_error_sticky <= 1;
            end
            if (rising) begin
                conversion_seen <= 1;
                interval_age <= 0;
                current_conversion_pair_count <= dual_sample_valid ? 1 : 0;
            end else if (conversion_seen) begin
                if (interval_age < CONVERSION_PERIOD) interval_age <= interval_age + 1'b1;
                if (dual_sample_valid && current_conversion_pair_count != 3)
                    current_conversion_pair_count <= current_conversion_pair_count + 1'b1;
            end
        end
    end
endmodule
