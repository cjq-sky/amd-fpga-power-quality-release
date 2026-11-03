create_bd_port -dir I main_reset
connect_bd_net [get_bd_ports main_reset] [get_bd_pins lab07_mmio/main_reset]
connect_bd_net [get_bd_ports main_reset] [get_bd_pins lab07_raw/main_reset]
create_bd_port -dir I raw_frame_valid
connect_bd_net [get_bd_ports raw_frame_valid] [get_bd_pins lab07_mmio/raw_frame_valid]
connect_bd_net [get_bd_ports raw_frame_valid] [get_bd_pins lab07_raw/owner_valid]
create_bd_port -dir I raw_bank_id
connect_bd_net [get_bd_ports raw_bank_id] [get_bd_pins lab07_mmio/raw_bank_id]
connect_bd_net [get_bd_ports raw_bank_id] [get_bd_pins lab07_raw/owner_bank]
create_bd_port -dir I -from 31 -to 0 raw_frame_id
connect_bd_net [get_bd_ports raw_frame_id] [get_bd_pins lab07_mmio/raw_frame_id]
connect_bd_net [get_bd_ports raw_frame_id] [get_bd_pins lab07_raw/owner_fid]
create_bd_port -dir I -from 31 -to 0 raw_owner_token
connect_bd_net [get_bd_ports raw_owner_token] [get_bd_pins lab07_mmio/raw_owner_token]
connect_bd_net [get_bd_ports raw_owner_token] [get_bd_pins lab07_raw/owner_token]
create_bd_port -dir I -from 7 -to 0 raw_status
connect_bd_net [get_bd_ports raw_status] [get_bd_pins lab07_mmio/raw_status]
connect_bd_net [get_bd_ports raw_status] [get_bd_pins lab07_raw/owner_status]
create_bd_port -dir I -from 7 -to 0 raw_bank_states
connect_bd_net [get_bd_ports raw_bank_states] [get_bd_pins lab07_mmio/raw_bank_states]
create_bd_port -dir O raw_ack_valid
connect_bd_net [get_bd_ports raw_ack_valid] [get_bd_pins lab07_mmio/raw_ack_valid]
create_bd_port -dir O raw_ack_bank_id
connect_bd_net [get_bd_ports raw_ack_bank_id] [get_bd_pins lab07_mmio/raw_ack_bank_id]
create_bd_port -dir O -from 31 -to 0 raw_ack_token
connect_bd_net [get_bd_ports raw_ack_token] [get_bd_pins lab07_mmio/raw_ack_token]
create_bd_port -dir I -from 31 -to 0 feature_snapshot_seq
connect_bd_net [get_bd_ports feature_snapshot_seq] [get_bd_pins lab07_mmio/feature_snapshot_seq]
create_bd_port -dir I feature_snapshot_valid
connect_bd_net [get_bd_ports feature_snapshot_valid] [get_bd_pins lab07_mmio/feature_snapshot_valid]
create_bd_port -dir I -from 31 -to 0 feature_frame_id
connect_bd_net [get_bd_ports feature_frame_id] [get_bd_pins lab07_mmio/feature_frame_id]
create_bd_port -dir I -from 8 -to 0 feature_valid_mask
connect_bd_net [get_bd_ports feature_valid_mask] [get_bd_pins lab07_mmio/feature_valid_mask]
create_bd_port -dir I feature_acquisition_valid
connect_bd_net [get_bd_ports feature_acquisition_valid] [get_bd_pins lab07_mmio/feature_acquisition_valid]
create_bd_port -dir I -from 7 -to 0 feature_time_status
connect_bd_net [get_bd_ports feature_time_status] [get_bd_pins lab07_mmio/feature_time_status]
create_bd_port -dir I -from 31 -to 0 feature_spectral_status
connect_bd_net [get_bd_ports feature_spectral_status] [get_bd_pins lab07_mmio/feature_spectral_status]
create_bd_port -dir I -from 31 -to 0 feature_numeric_status
connect_bd_net [get_bd_ports feature_numeric_status] [get_bd_pins lab07_mmio/feature_numeric_status]
create_bd_port -dir I -from 3 -to 0 feature_formal_identity
connect_bd_net [get_bd_ports feature_formal_identity] [get_bd_pins lab07_mmio/feature_formal_identity]
create_bd_port -dir I -from 15 -to 0 ch1_rms
connect_bd_net [get_bd_ports ch1_rms] [get_bd_pins lab07_mmio/ch1_rms]
create_bd_port -dir I -from 15 -to 0 ch1_peak
connect_bd_net [get_bd_ports ch1_peak] [get_bd_pins lab07_mmio/ch1_peak]
create_bd_port -dir I -from 15 -to 0 ch1_crest
connect_bd_net [get_bd_ports ch1_crest] [get_bd_pins lab07_mmio/ch1_crest]
create_bd_port -dir I -from 31 -to 0 frequency_ch1_mhz
connect_bd_net [get_bd_ports frequency_ch1_mhz] [get_bd_pins lab07_mmio/frequency_ch1_mhz]
create_bd_port -dir I -from 31 -to 0 ch1_h1
connect_bd_net [get_bd_ports ch1_h1] [get_bd_pins lab07_mmio/ch1_h1]
create_bd_port -dir I -from 31 -to 0 ch1_h3
connect_bd_net [get_bd_ports ch1_h3] [get_bd_pins lab07_mmio/ch1_h3]
create_bd_port -dir I -from 31 -to 0 ch1_h5
connect_bd_net [get_bd_ports ch1_h5] [get_bd_pins lab07_mmio/ch1_h5]
create_bd_port -dir I -from 31 -to 0 ch1_h7
connect_bd_net [get_bd_ports ch1_h7] [get_bd_pins lab07_mmio/ch1_h7]
create_bd_port -dir I -from 31 -to 0 ch1_h9
connect_bd_net [get_bd_ports ch1_h9] [get_bd_pins lab07_mmio/ch1_h9]
create_bd_port -dir I -from 31 -to 0 ch1_thd
connect_bd_net [get_bd_ports ch1_thd] [get_bd_pins lab07_mmio/ch1_thd]
create_bd_port -dir I -from 15 -to 0 ch2_rms
connect_bd_net [get_bd_ports ch2_rms] [get_bd_pins lab07_mmio/ch2_rms]
create_bd_port -dir I -from 15 -to 0 ch2_peak
connect_bd_net [get_bd_ports ch2_peak] [get_bd_pins lab07_mmio/ch2_peak]
create_bd_port -dir I -from 15 -to 0 ch2_crest
connect_bd_net [get_bd_ports ch2_crest] [get_bd_pins lab07_mmio/ch2_crest]
create_bd_port -dir I -from 31 -to 0 ch2_h1
connect_bd_net [get_bd_ports ch2_h1] [get_bd_pins lab07_mmio/ch2_h1]
create_bd_port -dir I -from 31 -to 0 ch2_h3
connect_bd_net [get_bd_ports ch2_h3] [get_bd_pins lab07_mmio/ch2_h3]
create_bd_port -dir I -from 31 -to 0 ch2_h5
connect_bd_net [get_bd_ports ch2_h5] [get_bd_pins lab07_mmio/ch2_h5]
create_bd_port -dir I -from 31 -to 0 ch2_h7
connect_bd_net [get_bd_ports ch2_h7] [get_bd_pins lab07_mmio/ch2_h7]
create_bd_port -dir I -from 31 -to 0 ch2_h9
connect_bd_net [get_bd_ports ch2_h9] [get_bd_pins lab07_mmio/ch2_h9]
create_bd_port -dir I -from 31 -to 0 ch2_thd
connect_bd_net [get_bd_ports ch2_thd] [get_bd_pins lab07_mmio/ch2_thd]
create_bd_port -dir I acquisition_fault_live
connect_bd_net [get_bd_ports acquisition_fault_live] [get_bd_pins lab07_mmio/acquisition_fault_live]
create_bd_port -dir I -from 7 -to 0 acquisition_fault_code_live
connect_bd_net [get_bd_ports acquisition_fault_code_live] [get_bd_pins lab07_mmio/acquisition_fault_code_live]
create_bd_port -dir I branch_mismatch_sticky
connect_bd_net [get_bd_ports branch_mismatch_sticky] [get_bd_pins lab07_mmio/branch_mismatch_sticky]
create_bd_port -dir I order_unknown_sticky
connect_bd_net [get_bd_ports order_unknown_sticky] [get_bd_pins lab07_mmio/order_unknown_sticky]
create_bd_port -dir I -from 31 -to 0 last_mismatch_time_id
connect_bd_net [get_bd_ports last_mismatch_time_id] [get_bd_pins lab07_mmio/last_mismatch_time_id]
create_bd_port -dir I -from 31 -to 0 last_mismatch_spectral_id
connect_bd_net [get_bd_ports last_mismatch_spectral_id] [get_bd_pins lab07_mmio/last_mismatch_spectral_id]
create_bd_port -dir I time_waiting_for_spectral
connect_bd_net [get_bd_ports time_waiting_for_spectral] [get_bd_pins lab07_mmio/time_waiting_for_spectral]
create_bd_port -dir I spectral_waiting_for_time
connect_bd_net [get_bd_ports spectral_waiting_for_time] [get_bd_pins lab07_mmio/spectral_waiting_for_time]
create_bd_port -dir I time_output_held
connect_bd_net [get_bd_ports time_output_held] [get_bd_pins lab07_mmio/time_output_held]
create_bd_port -dir I spectral_output_held
connect_bd_net [get_bd_ports spectral_output_held] [get_bd_pins lab07_mmio/spectral_output_held]
create_bd_port -dir I lab05_summary_overrun_live
connect_bd_net [get_bd_ports lab05_summary_overrun_live] [get_bd_pins lab07_mmio/lab05_summary_overrun_live]
create_bd_port -dir I lab05_result_overrun_live
connect_bd_net [get_bd_ports lab05_result_overrun_live] [get_bd_pins lab07_mmio/lab05_result_overrun_live]
create_bd_port -dir I lab06_bank_overrun_sticky
connect_bd_net [get_bd_ports lab06_bank_overrun_sticky] [get_bd_pins lab07_mmio/lab06_bank_overrun_sticky]
create_bd_port -dir I lab06_frame_error_sticky
connect_bd_net [get_bd_ports lab06_frame_error_sticky] [get_bd_pins lab07_mmio/lab06_frame_error_sticky]
create_bd_port -dir I lab06_protocol_error_sticky
connect_bd_net [get_bd_ports lab06_protocol_error_sticky] [get_bd_pins lab07_mmio/lab06_protocol_error_sticky]
create_bd_port -dir I -from 31 -to 0 last_successful_feature_frame_id
connect_bd_net [get_bd_ports last_successful_feature_frame_id] [get_bd_pins lab07_mmio/last_successful_feature_frame_id]
create_bd_port -dir I -from 31 -to 0 snapshot_update_counter
connect_bd_net [get_bd_ports snapshot_update_counter] [get_bd_pins lab07_mmio/snapshot_update_counter]
create_bd_port -dir I raw_drop_sticky
connect_bd_net [get_bd_ports raw_drop_sticky] [get_bd_pins lab07_mmio/raw_drop_sticky]
create_bd_port -dir I -from 31 -to 0 raw_drop_count
connect_bd_net [get_bd_ports raw_drop_count] [get_bd_pins lab07_mmio/raw_drop_count]
create_bd_port -dir I raw_protocol_sticky
connect_bd_net [get_bd_ports raw_protocol_sticky] [get_bd_pins lab07_mmio/raw_protocol_sticky]
create_bd_port -dir I raw_ack_error_sticky
connect_bd_net [get_bd_ports raw_ack_error_sticky] [get_bd_pins lab07_mmio/raw_ack_error_sticky]
create_bd_port -dir I raw_token_exhausted_sticky
connect_bd_net [get_bd_ports raw_token_exhausted_sticky] [get_bd_pins lab07_mmio/raw_token_exhausted_sticky]
create_bd_port -dir O raw_read_en
connect_bd_net [get_bd_ports raw_read_en] [get_bd_pins lab07_raw/raw_read_en]
create_bd_port -dir O raw_read_bank_id
connect_bd_net [get_bd_ports raw_read_bank_id] [get_bd_pins lab07_raw/raw_read_bank_id]
create_bd_port -dir O -from 10 -to 0 raw_read_index
connect_bd_net [get_bd_ports raw_read_index] [get_bd_pins lab07_raw/raw_read_index]
create_bd_port -dir I raw_read_valid
connect_bd_net [get_bd_ports raw_read_valid] [get_bd_pins lab07_raw/raw_read_valid]
create_bd_port -dir I -from 31 -to 0 raw_read_data
connect_bd_net [get_bd_ports raw_read_data] [get_bd_pins lab07_raw/raw_read_data]
connect_bd_net [get_bd_pins lab07_raw/read_busy] [get_bd_pins lab07_mmio/raw_read_busy]
connect_bd_net [get_bd_pins lab07_raw/read_start] [get_bd_pins lab07_mmio/raw_read_start]
connect_bd_net [get_bd_pins lab07_mmio/ack_reservation] [get_bd_pins lab07_raw/ack_reservation]
