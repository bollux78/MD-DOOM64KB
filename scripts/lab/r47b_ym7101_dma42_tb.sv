// R47B-RTL stage 1: actual pinned Nuked YM7101 clock/reset smoke and VCD.
// NOT yet VDP register protocol, VBlank DMA or full-MD bus timing.
`timescale 1ns/1ps

module r47b_ym7101_dma42;
  reg MCLK=0, RESET=0;
  reg [22:0] cpu_addr=23'h7fffff;
  reg [15:0] cpu_data=16'hffff;
  reg cpu_as_n=1, cpu_uds_n=1, cpu_lds_n=1, cpu_rw_n=1;
  reg cpu_sel=1'b1;
  reg cpu_bg_n=1'b1; // 68000 /BG, drive low to model granted bus

  reg MCLK_e=0;
  always @(posedge MCLK) MCLK_e <= ~MCLK_e; // matches md_board.v
  always #9.313 MCLK=~MCLK; // approx NTSC 53.69 MHz oscillator
  wire vdp_hclk1,vdp_de_h,vdp_de_v,vdp_dma,vdp_dma_oe_early;
  wire vdp_hsync2,vdp_vsync2,VSYNC;
  wire [7:0] DAC_R,DAC_G,DAC_B;
  wire [7:0] AD_o,RD_o;
  wire AD_d,RD_d;
  wire [15:0] CD_o;
  wire CD_d;
  wire [22:0] CA_o;
  wire CA_d;
  wire [7:0] RA;
  wire [15:0] SOUND;
  wire CLK0,CLK1_next,CLK0_next,SBCR,CLK1_o;
  wire SE1,SE0,SC,RAS1,CAS1,WE1,WE0,OE1,YS;
  wire SPA_B_pull,CSYNC_pull,HSYNC_pull;
  wire INT_pull,BR_pull,BGACK_pull,IPL1_pull,IPL2_pull,DTACK_pull;
  wire UWR,LWR,OE0,CAS0,RAS0,vdp_intfield,vdp_m5,vdp_rs1,vdp_m2,vdp_lcb,vdp_psg_clk1;
  wire EDCLK_o,EDCLK_d;

  // Idle 68000 bus with all active-low strobes deasserted.
  // CD_i / CA_i are NOT a functional DMA cartridge memory model here.
  ym7101 dut(
    .MCLK(MCLK),.RESET(RESET),.PAL(1'b0),.HL(1'b0),
    .SD(8'h00),.SE1(SE1),.SE0(SE0),.SC(SC),
    .RAS1(RAS1),.CAS1(CAS1),.WE1(WE1),.WE0(WE0),.OE1(OE1),
    .RD_i(8'h00),.RD_o(RD_o),.RD_d(RD_d),
    .DAC_R(DAC_R),.DAC_G(DAC_G),.DAC_B(DAC_B),
    .AD_i(8'h00),.AD_o(AD_o),.AD_d(AD_d),.YS(YS),
    .SPA_B_i(1'b1),.SPA_B_pull(SPA_B_pull),.VSYNC(VSYNC),
    .CSYNC_i(1'b1),.CSYNC_pull(CSYNC_pull),
    .HSYNC_i(1'b1),.HSYNC_pull(HSYNC_pull),
    .SEL0(cpu_sel),.CLK1_i(CLK1_o),.CLK1_o(CLK1_o),
    .SBCR(SBCR),.CLK0(CLK0),.CLK1_next(CLK1_next),.CLK0_next(CLK0_next),
    .MCLK_e(MCLK_e),.EDCLK_i(1'b0),.EDCLK_o(EDCLK_o),.EDCLK_d(EDCLK_d),
    .CD_i(cpu_data),.CD_o(CD_o),.CD_d(CD_d),
    .CA_i(cpu_addr),.CA_o(CA_o),.CA_d(CA_d),.SOUND(SOUND),
    .INT_pull(INT_pull),.BR_pull(BR_pull),.BGACK_i(1'b1),
    .BGACK_pull(BGACK_pull),.BG(cpu_bg_n),.MREQ(1'b1),
    .INTAK(1'b1),.IPL1_pull(IPL1_pull),.IPL2_pull(IPL2_pull),
    .IORQ(1'b1),.RD(1'b1),.WR(1'b1),.M1(1'b1),
    .AS(cpu_as_n),.UDS(cpu_uds_n),.LDS(cpu_lds_n),.RW(cpu_rw_n),
    .DTACK_i(1'b1),.DTACK_pull(DTACK_pull),
    .UWR(UWR),.LWR(LWR),.OE0(OE0),.CAS0(CAS0),.RAS0(RAS0),.RA(RA),
    .ext_test_2(1'b0),.vdp_hclk1(vdp_hclk1),.vdp_intfield(vdp_intfield),
    .vdp_de_h(vdp_de_h),.vdp_de_v(vdp_de_v),.vdp_m5(vdp_m5),
    .vdp_rs1(vdp_rs1),.vdp_m2(vdp_m2),.vdp_lcb(vdp_lcb),
    .vdp_psg_clk1(vdp_psg_clk1),.vdp_hsync2(vdp_hsync2),
    .vdp_vsync2(vdp_vsync2),.vdp_cramdot_dis(1'b0),
    .vdp_dma_oe_early(vdp_dma_oe_early),.vdp_dma(vdp_dma)
  );

  integer mcycles=0,hclk_edges=0,vdma_high=0;
  integer known_clock=0;
  integer dma_after_reset=0;
  integer de_h_known=0;
  integer de_v_known=0;
  integer dma_unknown=0;
  reg old_hclk=0;
  always @(posedge MCLK) begin
    mcycles<=mcycles+1;
    if(vdp_hclk1!==1'bx && vdp_hclk1!==1'bz)
      known_clock<=known_clock+1;
    if(old_hclk===1'b0 && vdp_hclk1===1'b1) hclk_edges<=hclk_edges+1;
    old_hclk<=vdp_hclk1;
    if(vdp_dma===1'b1) begin
      vdma_high<=vdma_high+1;
      if(RESET===1'b1) dma_after_reset<=dma_after_reset+1;
    end
    if(vdp_dma===1'bx || vdp_dma===1'bz) dma_unknown<=dma_unknown+1;
    if(vdp_de_h===1'b0 || vdp_de_h===1'b1) de_h_known<=de_h_known+1;
    if(vdp_de_v===1'b0 || vdp_de_v===1'b1) de_v_known<=de_v_known+1;
  end

  integer register_write_pulses=0, m5_seen=0, cpu_write_windows=0;
  always @(posedge MCLK) begin
    if(RESET && dut.w217===1'b1) register_write_pulses<=register_write_pulses+1;
    if(RESET && dut.reg_m5===1'b1) m5_seen<=m5_seen+1;
    if(RESET && dut.cpu_as===1'b1 && dut.cpu_rw===1'b1) cpu_write_windows<=cpu_write_windows+1;
  end

  // Deliberately conservative 68000-like strobe: address/data stable
  // before /AS and /UDS /LDS, held across many CPU clock phases.
  // This is not a complete 68000 timing or DTACK handshake model.
  task write_vdp;
    input [22:0] address;
    input [15:0] data;
    begin
      @(negedge MCLK);
      cpu_addr=address; cpu_data=data; cpu_rw_n=1'b0;
      repeat(32) @(negedge MCLK);
      cpu_as_n=1'b0; cpu_uds_n=1'b0; cpu_lds_n=1'b0;
      repeat(14) @(negedge MCLK);
      cpu_as_n=1'b1; cpu_uds_n=1'b1; cpu_lds_n=1'b1;
      repeat(64) @(negedge MCLK);
      cpu_rw_n=1'b1;
    end
  endtask

  integer dma_post_command=0, dma_early_post_command=0;
  integer cmd_second_pulses=0, cmd_start_pulses=0, dma_state_pulses=0, dma_armed_pulses=0, grant_accept_pulses=0;
  always @(posedge MCLK) if(RESET) begin
    if(dut.w168===1'b1) cmd_second_pulses<=cmd_second_pulses+1;
    if(dut.w182===1'b1) cmd_start_pulses<=cmd_start_pulses+1;
    if(dut.t3===1'b1) dma_state_pulses<=dma_state_pulses+1;
    if(dut.t4===1'b1) dma_armed_pulses<=dma_armed_pulses+1;
    if(dut.w5===1'b1) grant_accept_pulses<=grant_accept_pulses+1;
  end
  reg command_sent=0;
  always @(posedge MCLK) if(command_sent) begin
    if(vdp_dma===1'b1) dma_post_command<=dma_post_command+1;
    if(vdp_dma_oe_early===1'b1) dma_early_post_command<=dma_early_post_command+1;
  end


  integer batch=0, dma_count=0, total_dma_clocks=0, total_mclk=0;
  integer batch_start, active_start, wait_cycles, active_count, batch_elapsed;
  integer longest_batch=0, shortest_batch=999999, total_batch_cycles=0;
  reg active_seen;
  initial begin
    $dumpfile("dist/r47b-rtl/r47b_ym7101_dma42.vcd");
    // Keep only essential signals to avoid multi-GB VCD for 42 DMAs.
    $dumpvars(0,MCLK,RESET,cpu_bg_n,cpu_as_n,cpu_rw_n,cpu_addr,cpu_data,
      vdp_dma,vdp_dma_oe_early,vdp_de_v,vdp_de_h,dut.reg_lg,dut.t3,dut.t4,dut.reg_m1,dut.reg_m5);
    repeat(128) @(negedge MCLK);
    RESET=1'b1;
    repeat(5000) @(negedge MCLK);
    write_vdp(23'h600002,16'h8114);
    write_vdp(23'h600002,16'h8F02);
    write_vdp(23'h600002,16'h9500);
    write_vdp(23'h600002,16'h9600);
    write_vdp(23'h600002,16'h9700);
    if(dut.reg_m5!==1'b1 || dut.reg_m1!==1'b1 || dut.reg_inc!==8'h02)
      $fatal(1,"FAIL: DMA prerequisites not configured");
    total_mclk=mcycles;
    for(batch=0;batch<42;batch=batch+1) begin
      cpu_bg_n=1'b1;
      repeat(64) @(negedge MCLK);
      batch_start=mcycles;
      write_vdp(23'h600002,16'h9326);
      write_vdp(23'h600002,16'h9400);
      write_vdp(23'h600002,16'h9500);
      write_vdp(23'h600002,16'h9600);
      if(dut.reg_lg!==16'hffd9)
        $fatal(1,"FAIL: DMA %0d length register not reloaded, lg=%h",batch,dut.reg_lg);
      write_vdp(23'h600002,16'h4000);
      write_vdp(23'h600002,16'h0080);
      cpu_bg_n=1'b0;
      cpu_data=16'hA55A;
      active_seen=0;
      active_count=0;
      wait_cycles=0;
      begin : dma_wait
        while(wait_cycles<8000) begin
          @(negedge MCLK);
          wait_cycles=wait_cycles+1;
          if(vdp_dma===1'b1) begin
            active_seen=1;
            active_count=active_count+1;
          end
          if(active_seen && dut.reg_lg===16'hffff && vdp_dma===1'b0)
            disable dma_wait;
        end
      end
      if(!active_seen || dut.reg_lg!==16'hffff)
        $fatal(1,"FAIL: DMA %0d did not complete request/count in 8k MCLK: seen=%b lg=%h",
          batch,active_seen,dut.reg_lg);
      batch_elapsed=mcycles-batch_start;
      if(batch_elapsed>longest_batch) longest_batch=batch_elapsed;
      if(batch_elapsed<shortest_batch) shortest_batch=batch_elapsed;
      total_batch_cycles=total_batch_cycles+batch_elapsed;
      total_dma_clocks=total_dma_clocks+active_count;
      dma_count=dma_count+1;
      $display("R47B_DMA42_BATCH index=%0d elapsed_mclk=%0d dma_active_mclk=%0d lg=%h",
        batch,batch_elapsed,active_count,dut.reg_lg);
    end
    $display("R47B_DMA42_RESULT completed=%0d total_batch_mclk=%0d dma_active_mclk=%0d min_batch=%0d max_batch=%0d",
      dma_count,total_batch_cycles,total_dma_clocks,shortest_batch,longest_batch);
    if(dma_count!=42) $fatal(1,"FAIL: fewer than 42 DMA requests completed");
    $display("PASS: 42 RTL DMA request/count sequences completed; VRAM data and VBlank fit NOT yet validated");
    $finish;
  end
endmodule
