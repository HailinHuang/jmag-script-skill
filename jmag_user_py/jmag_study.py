# -*- coding: utf-8 -*-
"""
Created on Mon Jun 24 09:10:24 2024

@author: ezzhh5
"""
from jmag.designer import *
import jmag_operation as jo
import get_winding_pattern as gw
import csv_operation as csvo
import time
import math
import cond_info_operation as cio
import layout_analysis as la 

# Global variables to store the initialized objects
app = None
model = None
mstudy = None
result = None

def initialize_jmag():
    global app, model, mstudy, result
    if app is None or model is None or mstudy is None or result is None:
        app = designer.GetApplication()
        model = app.GetCurrentModel()
        mstudy = app.GetCurrentStudy()
        result = app.GetCurrentResult()
    return (app, model, mstudy, result)

def set_operation_points_get_simple_results(Model_Para,speed,Irms,angle):
##### Initial Rotor parameters #######
    Tname = 'Tavg'
    Speedname = 'RPM'
    Iname = 'Irms'
    IAnglename = 'Phase_Advance'
    study = Model_Para.study
    case = Model_Para.case
    jo.mstudy.DeleteResult()
    jo.set_para(Speedname,speed,study,case)
    jo.set_para(Iname,Irms,study,case)
    jo.set_para(IAnglename,angle,study,case)
    jo.run_case(study,case)
    Torque=round(jo.get_data(Tname,study,case),3)
    CuLoss_eff=round(jo.get_data('ActiveCopperLoss',study,case),1)
    DCLoss_eff=round(jo.get_data('Active_DC_CopperLoss',study,case),1)
    ACLoss_eff=CuLoss_eff - DCLoss_eff
    Vline = round(jo.get_data('Vline',study,case),1)
    StatorIronLoss = round(jo.get_data('StatorIronLoss',study,case),3)
    RotorIronLoss = round(jo.get_data('RotorIronLoss',study,case),3)
    PMLoss=round(jo.get_data('PM_Loss',study,case),3)
    EndW_DC_CopperLoss = round(jo.get_data('EndW_DC_CopperLoss',study,case),3)
    jo.mstudy.DeleteResult()
    return (Torque,Vline,CuLoss_eff,DCLoss_eff,ACLoss_eff,EndW_DC_CopperLoss,StatorIronLoss,RotorIronLoss,PMLoss)


def Set_layers_slots_phase_shift_get_Loss_Efficiency(Model_Para,Winding_Para,Layout_Para,Stator_Para,EW_info,TP_info,DataAddress):
    num_layers = Winding_Para.num_layers
    num_slots = Winding_Para.num_slots
    num_poles = Winding_Para.num_poles
    num_phases  =Winding_Para.num_phases
    pattern_name = 'q_03'
    study = Model_Para.study
    case = Model_Para.case
    ksw = Stator_Para.ksw
    kso = Stator_Para.kso
    layerRange = [4,5,6,7,8,9,10]
    qRange = [2,3,4,5]
    TN_Speed=[15000]
    TN_Current = [360]
    TN_Phase = [81]
    CSVData = []
    CSVData.append(['numLayer','numSlots','FillFactor','Speed','Irms','Angle','Torque','Vline','CuLoss','Active_DCLoss','Active_ACLoss','Total_DC_Ratio','EW_DC_CuLoss','StatorIronLoss','RotorIronLoss','PMLoss','Efficiency','R_ew_phase','L_ew_phase','Length_ew_phase'])
    for layer in layerRange:
        num_layers = layer
        for q in qRange:
            num_slots = int(num_poles*num_phases*q)
            ab = q
            Stator_Para,Winding_Para,Inslot_Para = jo.initilize_para(Model_Para,ksw,kso,q,num_poles,num_layers,num_phases,num_slots,ab)
            cond_info = gw.Winding_Phase_division(Winding_Para,Layout_Para)
            start_conductor_ids, db_conductor_id = gw.get_winding_layout(pattern_name,TP_info,Winding_Para,Layout_Para)
            cond_info = cio.update_cond_info_with_branch_data(cond_info, db_conductor_id)
            results = la.analyze_database(db_conductor_id, Winding_Para, Layout_Para)
            jo.Full_Stator_Assignment(Stator_Para,Inslot_Para,Winding_Para,Model_Para,EW_info,cond_info,results)
            R_PhaseEndW, L_PhaseEndW, PhaseEndW_Length = jo.end_winding_calc.calculate_end_parameters_by_results(Winding_Para,Model_Para,Stator_Para,Inslot_Para,EW_info,results)
            # jo.model.CloseCadLink()
            Slot_Fill_Factor = jo.get_data('Slot_Fill_Factor',study,case)

            for i in range(len(TN_Speed)):
                speed = TN_Speed[i]
                Irms0 = TN_Current[i]
                angle = TN_Phase[i]
                Irms = Irms0*6/num_layers
                Torque,Vline,CuLoss,Active_DCLoss,Active_ACLoss,EW_DCLoss,StatorIronLoss,RotorIronLoss,PMLoss = set_operation_points_get_simple_results(Model_Para,speed,Irms,angle)
                Total_DC_Ratio = (Active_DCLoss+Active_ACLoss)/Active_ACLoss
                Efficiency = Torque * speed/60*2*3.1416 / (Torque * speed/60*2*3.1416 + CuLoss + StatorIronLoss + RotorIronLoss + PMLoss + EW_DCLoss)
                CSVData.append([num_layers,num_slots,Slot_Fill_Factor,speed,Irms,angle,Torque,Vline,CuLoss,Active_DCLoss,Active_ACLoss,Total_DC_Ratio,EW_DCLoss,StatorIronLoss,RotorIronLoss,PMLoss,Efficiency,R_PhaseEndW,L_PhaseEndW,PhaseEndW_Length])
    csvo.output_to_csv(DataAddress,CSVData)  
    
def Calculate_Drive_Cycle_Efficiency(Winding_Para,Layout_Para,Model_Para):
    # Shared global cache table for (I, Deg): (T, V, Loss)
    jo.simulation_cache.clear()
    
    app, model, mstudy, result = initialize_jmag()
    ##### Initial Rotor parameters #######
    Tname = 'Tmec'
    Speedname = 'RPM'
    Iname = 'Irms'
    IAnglename = 'Phase_Advance'
    num_layers = Winding_Para.num_layers
    phase_shift = Layout_Para.phase_shift
    pattern_name = Layout_Para.pattern_name
    q = Winding_Para.q
    case = Model_Para.case
    study = Model_Para.study
    Ilimit = 500
    IRange = [0,Ilimit]
    IStep = 1
    IAngleStep = 0.1
    IAngleRange = [0,90]
    Vlimit = 650
    Step0 = 5
    
    TN_Speed=[2865,4358,1915,7239,8292,831]
    TN_Torque=[315,155,237,77,98,8]
    TN_Current = [256,139,199,86,112,10]
    TN_Phase = [41.3,32,37.1,47,54.5,4.7]
    TN_Weight = [4,7,8,11,30,40]
    TN_Speed=[8292]
    TN_Torque=[98]
    
    CSVData=[]
    CSVData.append(['No','Speed','ObjTorque','Current','PhaseAdvance','FEATorque','Active_CopperLoss','End_DC_CopperLoss','IronLoss_Stator','IronLoss_Rotor','PMloss','TotalLoss','Vline','Efficiency'])
    DataAddress='D:\CumminsMachine\Efficiency_CARB_HHDDT_Points_q='+str(q)+'Nl='+str(num_layers)+'phase_shift='+str(phase_shift)+'_pattern'+pattern_name+'.csv'
    mstudy.GetDesignTable().SetCaseLabelFormat(u"Irms = %Irms% Phase = %Phase_Advance% Speed = %RPM%")
    Weight_Efficiency = 0
    # mstudy.DeleteResultCase(case)
    # run_case(study,case)
    for i in range(len(TN_Speed)):
        mstudy.DeleteResultCase(case)
        time.sleep(3)
        jo.set_para(Speedname,TN_Speed[i],study,case)
        objT = TN_Torque[i]
        # point=jo.MinI_objT_noVlimit(Tname,objT,Iname,IRange,IStep,IAnglename,IAngleRange,IAngleStep,study,case,Step0)
        # PhaseValue = point[0][1]
        # IValue = point[0][0]
        # Vline=round(jo.get_Vline(study,case,Step0),1)
        PhaseValue = 28.2
        IValue = 93
        Vline = 777
        if Vline > Vlimit:
            #### Set the new range of I_angle and current
            IAngleRange = [PhaseValue,90]
            IRange = [IValue,Ilimit]
            point=jo.MinI_objT_Vlimit(Tname,objT,Iname,IRange,IStep,IAnglename,IAngleRange,IAngleStep,Vlimit,study,case,Step0)
        jo.set_paras([Iname,IAnglename],[point[0][0],point[0][1]],study,case)  
        CurrentValue = point[0][0] 
        PhaseValue = point[0][1]
        
        jo.run_case(study,case)
        Vline = jo.get_data('Vline',study,case)
        Torque=round(jo.get_data(Tname,study,case),3)
        CuLoss_eff=round(jo.get_data('ActiveCopperLoss',study,case),1) 
        CuLoss_end=round(jo.get_data('EndW_DC_CopperLoss',study,case),1) 
        IronLoss_Stator=round(jo.get_data('StatorIronLoss',study,case),1) 
        IronLoss_Rotor=round(jo.get_data('RotorIronLoss',study,case),1)
        PMloss=round(jo.get_data('PM_Loss',study,case),2)
        Losstotal=IronLoss_Stator+IronLoss_Rotor+PMloss+CuLoss_end+CuLoss_eff
        Losstotal=IronLoss_Stator+IronLoss_Rotor+PMloss+CuLoss_end+CuLoss_eff
        Efficiency=round(Torque*TN_Speed[i]/(Torque*TN_Speed[i]+Losstotal*30/math.pi)*100,2)
        CSVData.append([i+1,TN_Speed[i],TN_Torque[i],CurrentValue,PhaseValue,Torque]+[CuLoss_eff,CuLoss_end,IronLoss_Stator,IronLoss_Rotor,PMloss,Losstotal,Vline,Efficiency])
        Weight_Efficiency += Efficiency * TN_Weight[i] / 100 ########### Calculate the weight efficiency
    CSVData.append(['Total', '', '', '', '', '', '', '', '', '', '', '', 'WeightEff', Weight_Efficiency])
    csvo.output_to_csv(DataAddress,CSVData)
    
