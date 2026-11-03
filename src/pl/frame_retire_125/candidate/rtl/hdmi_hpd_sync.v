// Status-only asynchronous HPDN input, synchronized to the control clock.
module hdmi_hpd_sync(input wire clk, input wire resetn,
                     input wire hpdn_async, output wire hpdn_sync);
  (* ASYNC_REG = "TRUE" *) reg sync_meta = 1'b1;
  (* ASYNC_REG = "TRUE" *) reg sync_out = 1'b1;
  always @(posedge clk) begin
    if (!resetn) begin sync_meta <= 1'b1; sync_out <= 1'b1; end
    else begin sync_meta <= hpdn_async; sync_out <= sync_meta; end
  end
  assign hpdn_sync = sync_out;
endmodule
