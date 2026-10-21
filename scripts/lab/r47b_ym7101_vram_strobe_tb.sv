// R47B-RTL stage 1: actual pinned Nuked YM7101 clock/reset smoke and VCD.
// NOT yet VDP register protocol, VBlank DMA or full-MD bus timing.
`timescale 1ns/1ps

module r47b_ym7101_vram_strobe;
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
  integer we0_falls=0,we1_falls=0,ras0_falls=0,ras1_falls=0,cas0_falls=0,cas1_falls=0;
  integer we0_low=0,we1_low=0,we0_high=0,we1_high=0,write_qualified=0;
  reg prev_we0=1,prev_we1=1,prev_ras0=1,prev_ras1=1,prev_cas0=1,prev_cas1=1;
  always @(posedge MCLK) begin
    if(command_sent) begin
      if(WE0===1'b0) we0_low<=we0_low+1;
      if(WE1===1'b0) we1_low<=we1_low+1;
      if(WE0===1'b1) we0_high<=we0_high+1;
      if(WE1===1'b1) we1_high<=we1_high+1;
      if(RAS1===1'b0 && CAS1===1'b0 && WE0===1'b0) write_qualified<=write_qualified+1;
      if(prev_we0===1'b1 && WE0===1'b0) we0_falls<=we0_falls+1;
      if(prev_we1===1'b1 && WE1===1'b0) we1_falls<=we1_falls+1;
      if(prev_ras0===1'b1 && RAS0===1'b0) ras0_falls<=ras0_falls+1;
      if(prev_ras1===1'b1 && RAS1===1'b0) ras1_falls<=ras1_falls+1;
      if(prev_cas0===1'b1 && CAS0===1'b0) cas0_falls<=cas0_falls+1;
      if(prev_cas1===1'b1 && CAS1===1'b0) cas1_falls<=cas1_falls+1;
    end
    prev_we0<=WE0;prev_we1<=WE1;prev_ras0<=RAS0;prev_ras1<=RAS1;prev_cas0<=CAS0;prev_cas1<=CAS1;
  end
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

  initial begin
    $dumpfile("dist/r47b-rtl/r47b_ym7101_vram_strobe.vcd");
    $dumpvars(0,MCLK,RESET,WE0,WE1,RAS0,RAS1,CAS0,CAS1,RA,AD_o,RD_o,AD_d,RD_d,CD_o,CD_d,vdp_dma,cpu_bg_n,dut.reg_lg);
    repeat(128) @(negedge MCLK);
    RESET=1'b1;
    repeat(5000) @(negedge MCLK);
    // Mode 5 + DMA enable, display disabled for a conservative first transfer.
    write_vdp(23'h600002,16'h8114);
    write_vdp(23'h600002,16'h8F02); // autoincrement 2
    write_vdp(23'h600002,16'h9326); // 38 words = 76 bytes
    write_vdp(23'h600002,16'h9400);
    write_vdp(23'h600002,16'h9500); // source = 0
    write_vdp(23'h600002,16'h9600);
    write_vdp(23'h600002,16'h9700); // DMA 68k-to-VRAM mode
    $display("R47B_DMA_REG m5=%b dma_enable=%b inc=%h lg=%h src=%h:%h mode=%h",
      dut.reg_m5,dut.reg_m1,dut.reg_inc,dut.reg_lg,dut.reg_sa_high,dut.reg_sa_low,dut.reg_dmd);
    if(dut.reg_m5!==1'b1 || dut.reg_m1!==1'b1 || dut.reg_inc!==8'h02)
      $fatal(1,"FAIL: DMA prerequisites not latched by RTL register interface");
    if(dut.reg_lg!==16'hffd9)
      $display("WARN: length counter differs from expected ones-complement value (verify RTL)");
    // VRAM DMA-write command (destination 0) 0x40000080.
    write_vdp(23'h600002,16'h4000);
    write_vdp(23'h600002,16'h0080);
    command_sent=1;
    cpu_bg_n=1'b0; // grant bus after DMA command, not before CPU programming
    // A deterministic placeholder cartridge data word. NOT a full DMA bus grant model.
    cpu_data=16'hA55A;
    repeat(8000) @(negedge MCLK);
    $display("R47B_DMA_RESULT dma_clocks=%0d early_clocks=%0d length=%h code=%h addr=%h cpu_bus=%h",
      dma_post_command,dma_early_post_command,dut.reg_lg,dut.reg_code,dut.reg_addr,dut.io_address);
    $display("R47B_DMA_DIAG second_word=%0d dma_start=%0d dma_state=%0d bgack=%b bg=%b",cmd_second_pulses,cmd_start_pulses,dma_state_pulses,dut.cpu_bgack,dut.cpu_bg);
    $display("R47B_DMA_GRANT armed=%0d grant_accept=%0d",dma_armed_pulses,grant_accept_pulses);
    $display("R47B_DMA_W5 dff22=%b dff2=%b bgack=%b dtack=%b cpu_sel=%b w37=%b cpu_clk1=%b t4=%b w62=%b",dut.dff22_l2,dut.dff2_l2,dut.cpu_bgack,dut.DTACK_i,dut.cpu_sel,dut.w37,dut.cpu_clk1,dut.t4,dut.w62);
    $display("R47B_VRAM_STROBES we0=%0d we1=%0d ras0=%0d ras1=%0d cas0=%0d cas1=%0d last_ra=%h last_ad=%h last_rd=%h",we0_falls,we1_falls,ras0_falls,ras1_falls,cas0_falls,cas1_falls,RA,AD_o,RD_o);
    $display("R47B_VRAM_WRITE_QUALIFIED clocks=%0d we0_low=%0d we0_high=%0d we1_low=%0d we1_high=%0d",write_qualified,we0_low,we0_high,we1_low,we1_high);
    if(dma_post_command==0)
      $fatal(1,"FAIL: DMA request not observed; no timing claim");
    $display("PASS: DMA request and VRAM external strobes observed for diagnosis; memory data not validated");
    $finish;
  end
endmodule
