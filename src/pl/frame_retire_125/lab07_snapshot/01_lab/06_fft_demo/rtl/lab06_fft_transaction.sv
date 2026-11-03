`timescale 1ns/1ps
// Exactly one owner/channel transaction at a time on the actual Xilinx FFT.
// A failed transaction resets/quarantines the core before accepting another.
module lab06_fft_transaction #(parameter TIMEOUT=100000)(
 input logic clk, reset, start,
 input logic [32:0] owner,
 output logic idle,
 input logic signed [24:0] sample,
 input logic sample_valid,
 input logic [32:0] sample_owner,
 output logic sample_ready,
 output logic signed [36:0] re, im,
 output logic [10:0] bin,
 output logic spectrum_valid, done, error,
 output logic [32:0] result_owner
);
 typedef enum logic [2:0] {QUARANTINE,IDLE,CONFIG,LOAD,UNLOAD,FINISH} state_t;
 state_t state=QUARANTINE;
 logic [3:0] reset_count=0;
 logic [11:0] ni,no;
 integer watchdog;
 logic core_resetn,cr,ir,ov,ol;
 logic [79:0] od;
 logic [15:0] ou;
 logic ev_start,ev_unexpected,ev_missing,ev_status,ev_in,ev_out;
 logic [63:0] idata;
 logic iv;
 logic bad;
 logic [7:0] error_causes, error_cause;
 logic [2:0] halt_events_seen;
 // Availability is the start-acceptance predicate, not just a state decode.
 // A pending stale output/event must not start a new owner's feature pipeline.
 assign idle=state==IDLE && !bad;
 assign core_resetn=!reset && state!=QUARANTINE;
 assign idata={32'b0,7'b0,sample};
 assign iv=state==LOAD && sample_valid && sample_owner==result_owner;
 assign sample_ready=state==LOAD && ir && sample_owner==result_owner;
 assign re=$signed(od[36:0]);
 assign im=$signed(od[76:40]);
 assign bin=ou[10:0];
 // Non-Realtime halt events indicate lossless waitstates (PG109), not damaged
 // arithmetic. Keep them observable; timeout and exact framing remain fatal.
 // Bits: unexpected TLAST, missing TLAST, owner, output state, bin, TLAST,
 // timeout, overlapping start. error_cause records the actual first fault.
 always_comb begin
  error_causes=0;
  error_causes[0]=ev_unexpected;
  error_causes[1]=ev_missing;
  error_causes[2]=state==LOAD && sample_valid && sample_owner!=result_owner;
  error_causes[3]=ov && state!=UNLOAD;
  error_causes[4]=ov && ou!={5'b0,no[10:0]};
  error_causes[5]=ov && ol!=(no==2047);
  error_causes[6]=(state==CONFIG || state==LOAD || state==UNLOAD) && watchdog>=TIMEOUT;
  error_causes[7]=start && state!=IDLE && state!=QUARANTINE;
 end
 // Avoid a combinational loop through the caller's start = idle && request.
 assign bad=|error_causes[5:0];
 assign spectrum_valid=state==UNLOAD && ov && !bad;
 lab06_fft core(
  .aclk(clk),.aresetn(core_resetn),
  .s_axis_config_tdata(8'h01),.s_axis_config_tvalid(state==CONFIG),.s_axis_config_tready(cr),
  .s_axis_data_tdata(idata),.s_axis_data_tvalid(iv),.s_axis_data_tready(ir),.s_axis_data_tlast(ni==2047),
  .m_axis_data_tdata(od),.m_axis_data_tuser(ou),.m_axis_data_tvalid(ov),.m_axis_data_tready(state==UNLOAD),.m_axis_data_tlast(ol),
  .event_frame_started(ev_start),.event_tlast_unexpected(ev_unexpected),.event_tlast_missing(ev_missing),
  .event_status_channel_halt(ev_status),.event_data_in_channel_halt(ev_in),.event_data_out_channel_halt(ev_out));
 always_ff @(posedge clk) begin
  done<=0; error<=0;
  if(reset) begin state<=QUARANTINE; reset_count<=0; ni<=0; no<=0; watchdog<=0; result_owner<=0; error_cause<=0;halt_events_seen<=0;end
  else if(state==QUARANTINE) begin
   if(reset_count==7) begin state<=IDLE; reset_count<=0; end
   else reset_count<=reset_count+1;
  end else if(|error_causes) begin
   error<=1; done<=1; error_cause<=error_causes;state<=QUARANTINE; reset_count<=0;
  end else begin
   if(state==CONFIG || state==LOAD || state==UNLOAD || state==FINISH)
    halt_events_seen<=halt_events_seen | {ev_status,ev_out,ev_in};
   watchdog<=watchdog+1;
   case(state)
    IDLE: if(start) begin result_owner<=owner; ni<=0; no<=0; watchdog<=0;error_cause<=0;halt_events_seen<=0;state<=CONFIG;end
    CONFIG: if(cr) state<=LOAD;
    LOAD: if(iv && ir) begin ni<=ni+1; if(ni==2047) state<=UNLOAD; end
    UNLOAD: if(ov) begin no<=no+1; if(no==2047) state<=FINISH; end
    FINISH: begin done<=1; state<=IDLE; watchdog<=0; end
    default: state<=QUARANTINE;
   endcase
  end
 end
endmodule
