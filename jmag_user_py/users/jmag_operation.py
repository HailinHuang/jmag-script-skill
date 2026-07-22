# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 15:29:53 2024

@author: ezzhh5
"""
import math
import csv
import end_winding_calc
from jmag.designer import *
import numpy as np
import csv_operation as csvo
from scipy import interpolate

# Global variables to store the initialized objects
app = None
model = None
mstudy = None
result = None

simulation_cache = {}

def initialize_jmag(force_refresh=False):
    """Return the current JMAG objects without treating a missing result as failure.

    A study can validly have no current result before it has been run.  The old
    implementation reattached to JMAG on every call in that state, which also
    made cached model/study identity unpredictable.
    """
    global app, model, mstudy, result
    if force_refresh or app is None or model is None or mstudy is None:
        app = designer.GetApplication()
        if app is None:
            raise RuntimeError("No JMAG application is available")
        model = app.GetCurrentModel()
        if model is None:
            raise RuntimeError("No current JMAG model is available")
        mstudy = app.GetCurrentStudy()
        if mstudy is None:
            raise RuntimeError("No current JMAG study is available")
        result = app.GetCurrentResult()
    return (app, model, mstudy, result)


def _activate_study(application, study):
    application.SetCurrentStudy(study)
    selected = application.GetCurrentStudy()
    if selected is None:
        raise RuntimeError("JMAG study not found: {!r}".format(study))
    return selected


def _normalize_cases(case, table):
    """Validate public one-based case numbers and return zero-based indexes."""
    if isinstance(case, bool):
        raise TypeError("case must be a 1-based integer or an iterable of integers")
    if isinstance(case, int):
        cases = [case]
        is_scalar = True
    else:
        if isinstance(case, (str, bytes)):
            raise TypeError("case must be a 1-based integer or an iterable of integers")
        try:
            cases = list(case)
        except TypeError as exc:
            raise TypeError(
                "case must be a 1-based integer or an iterable of integers"
            ) from exc
        is_scalar = False
    if not cases:
        raise ValueError("case must not be empty")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in cases):
        raise TypeError("every case must be a 1-based integer")
    if len(set(cases)) != len(cases):
        raise ValueError("case must not contain duplicates")
    count = int(table.NumCases())
    for value in cases:
        if value < 1 or value > count:
            raise ValueError("case must be between 1 and {}; got {}".format(count, value))
    return [value - 1 for value in cases], is_scalar


def _parameter_index(table, name):
    expected = "Equation parameters: " + name
    for index in range(int(table.NumParameters())):
        if (table.ParameterTypeName(index) == "Equation"
                and table.ParameterName(index) == expected):
            return index
    raise KeyError("JMAG equation parameter not found: {}".format(name))


def _read_scalar(study_object, name, case_index):
    table = study_object.GetDesignTable()
    try:
        _parameter_index(table, name)
    except KeyError:
        response = study_object.GetResponseData(name, case_index)
        if response is None or len(response) == 0:
            raise KeyError(
                "JMAG value not found: {!r} for case {}".format(name, case_index + 1)
            )
        if len(response) != 1:
            raise ValueError(
                "Expected one scalar for {!r}; got {} values".format(name, len(response))
            )
        return response[0]
    return table.GetEquation(name).GetValue(case_index)


def _normalize_assignments(varnames, varvalues):
    names = [varnames] if isinstance(varnames, str) else list(varnames)
    if isinstance(varvalues, (str, bytes)) or not hasattr(varvalues, "__iter__"):
        values = [varvalues]
    else:
        values = list(varvalues)
    if not names:
        raise ValueError("varnames must not be empty")
    if any(not isinstance(name, str) or not name for name in names):
        raise TypeError("every parameter name must be a non-empty string")
    if len(set(names)) != len(names):
        raise ValueError("varnames must not contain duplicates")
    if len(names) != len(values):
        raise ValueError("varnames and varvalues must have the same length")
    return list(zip(names, values))

def open_file(file_path):
    app,model,mstudy,result = initialize_jmag()
    # app.Save()
    app.NewProject(u"Untitled")
    app.Load(file_path)
    
def delete_result(case):
    mstudy.DeleteResultCase(case)

def jmag_main_operation(Winding_Para,Inslot_Para,EW_info,cond_info,Layout_Para,Stator_Para,Model_Para,results):
    #Set the inslot_dimensions####
    study = Model_Para.study
    case = Model_Para.case
    set_inslot_dimensions(study,case,Inslot_Para)
    Winding_Cond_Assignment(Winding_Para,Model_Para,cond_info)
    set_para('Parallel_Branch', Winding_Para.ab, study, case)
    set_para('PhaseShift', Layout_Para.phase_shift, study, case)
    ###Set the width ratio of stator slot and stator slot opening.
    set_stator_by_ratio(study,case,Stator_Para,Winding_Para)
    Process_conductor_layer_settings(Winding_Para,Model_Para)
    Coil_EndWinding_and_Magnet_Loss_Setting(Winding_Para,Model_Para,Stator_Para,Inslot_Para,EW_info,results)
    model.CloseCadLink()

def FFT_1D_Amp(data,max_order): #fft get the amplitude value
	#ttt=time.time_ns()
	import numpy as np
	Amp=[]
	try:
		len(data[0])
	except:
		data=[data]
	for di in data:
		ff = np.fft.fft(di)
		Amp.append([abs(ff[i])/(len(di)/2) if i>0 else abs(ff[i])/(len(di)/2)/2 for i in range(max_order + 1)])
	##ttt=time.time_ns()-ttt
	#print('FFT:',ttt/1e9)
	return Amp if len(data)>1 else Amp[0]	

def get_phase_code(phase_index):
    if phase_index >= 1:
        phase_code = chr(ord('A') + phase_index - 1)
        return phase_code
    else:
        return None  # Return None or a default value for invalid inputs

def get_phase_index(slot, layer, cond_info):
    for info in cond_info:
        if info[0] == slot and info[1] == layer:
            return info[2]
    return None  # Return None if no matching slot and layer are found

def get_pole_index(slot, layer, cond_info):
    for info in cond_info:
        if info[0] == slot and info[1] == layer:
            return info[6]
    return None  # Return None if no matching slot and layer are found

# Main functionalities in JMAG
def run_case(study, case, clear_results=False):
    """Run exactly the requested one-based cases and restore the active case."""
    application, _, _, _ = initialize_jmag()
    selected = _activate_study(application, study)
    indexes, _ = _normalize_cases(case, selected.GetDesignTable())
    if selected.GetReport().HasWarningMessage():
        selected.ApplyAllCasesCadParameters()
    if clear_results:
        selected.DeleteResult()
    original_case = selected.GetCurrentCase()
    try:
        for case_index in indexes:
            selected.SetCurrentCase(case_index)
            selected.Run()
    finally:
        selected.SetCurrentCase(original_case)

##########Get and Set Data/Para#########################
def get_data(objname, study, case):
    """Read a scalar value; a case collection retains the legacy sum contract."""
    if not isinstance(objname, str) or not objname:
        raise TypeError("objname must be a non-empty string")
    application, _, _, _ = initialize_jmag()
    selected = _activate_study(application, study)
    indexes, is_scalar = _normalize_cases(case, selected.GetDesignTable())
    values = [_read_scalar(selected, objname, index) for index in indexes]
    return values[0] if is_scalar else sum(values)

def get_datas(objname, study, case):
    """Read multiple named scalars without iterating a single name by character."""
    names = [objname] if isinstance(objname, str) else list(objname)
    if not names:
        raise ValueError("objname must not be empty")
    if any(not isinstance(name, str) or not name for name in names):
        raise TypeError("every object name must be a non-empty string")
    return [get_data(name, study, case) for name in names]

def set_para(varname, varvalue, study, case, *, delete_results=True):
    """Set one equation parameter after validation.

    ``delete_results`` remains True for legacy compatibility, but is explicit
    and can be disabled by orchestration that manages result lifecycle itself.
    """
    set_paras([varname], [varvalue], study, case, delete_results=delete_results)

def set_paras(varnames, varvalues, study, case, *, delete_results=True):
    """Atomically validate and set equation parameters for one or more cases."""
    _set_parameters(
        varnames, varvalues, study, case, delete_results=delete_results
    )


def _set_parameters(varnames, varvalues, study, case, *, delete_results):
    """Internal implementation that reports whether any value changed."""
    assignments = _normalize_assignments(varnames, varvalues)
    application, _, _, _ = initialize_jmag()
    selected = _activate_study(application, study)
    table = selected.GetDesignTable()
    indexes, _ = _normalize_cases(case, table)

    # Resolve every name and case before any destructive or mutating call.
    resolved = [(_parameter_index(table, name), value) for name, value in assignments]
    writes = []
    for case_index in indexes:
        for (name, value), (parameter_index, _) in zip(assignments, resolved):
            current = table.GetEquation(name).GetValue(case_index)
            if current != value:
                writes.append((case_index, parameter_index, value))
    if not writes:
        return False
    if delete_results:
        selected.DeleteResult()
    for case_index, parameter_index, value in writes:
        table.SetValue(case_index, parameter_index, str(value))
    original_case = selected.GetCurrentCase()
    try:
        if len(indexes) == 1:
            selected.SetCurrentCase(indexes[0])
            selected.ApplyCadParameters()
        else:
            selected.ApplyAllCasesCadParameters()
    finally:
        selected.SetCurrentCase(original_case)
    return True
                
def get_datas_set_paras(objname, varname, varvalue, study, case):
    """Set parameters, run only changed/requested cases, then read scalars."""
    changed = _set_parameters(
        varname, varvalue, study, case, delete_results=False
    )
    if changed:
        run_case(study, case, clear_results=True)
    try:
        return get_datas(objname, study, case)
    except KeyError:
        if changed:
            raise
        run_case(study, case, clear_results=False)
        return get_datas(objname, study, case)

def set_para_leave_result(varname, varvalue, study, case):
    """Compatibility wrapper for an explicit write that preserves results."""
    set_para(varname, varvalue, study, case, delete_results=False)

##########Get and Set Data/Para#########################


def set_Stator_Iron_Loss(model,study,statorname='Stator'):
	app.SetCurrentStudy(study)
	app.GetModel(model).GetStudy(study).CreateCondition(u"Ironloss", u"Stator")
	Condition = app.GetModel(model).GetStudy(study).GetCondition("Stator")
	Condition.SetValue(u"BasicFrequencyType", 2)
	Condition.SetValue(u"BasicFrequency", u"Freq")
	Condition.ClearParts()
	sel = Condition.GetSelection()
	sel.SelectPart(statorname)
	app.GetModel(model).GetStudy(0).GetCondition("Stator").AddSelected(sel)
	parameter = app.CreateResponseDataParameter(u"StatorIronLoss")
	parameter.SetCalculationType(u"Maximum")
	parameter.SetUnit(u"Hz")
	parameter.SetVariable(u"StatorIronLoss")
	parameter.SetAllLine(False)
	parameter.SetCaseRangeType(0)
	parameter.SetLine(2)
	app.GetStudy(study).CreateParametricDataFromTable(u"Iron Loss (Iron loss)", parameter)
    
def delete_Stator_Iron_Loss(model,study):
	app.GetModel(model).GetStudy(study).DeleteCondition("Stator")
	app.GetModel(model).GetStudy(study).DeleteParametricData('StatorIronLoss')

def get_llVoltage_Div_period(study,case,Step0):   
    ###Includded in run case 
#ttt=time.time_ns()
    TempVAddress = "TempVline.csv"
    app.SetCurrentStudy(study)
    if isinstance(case,int): Div_Period = get_data('Div_Period',study,case)
    if isinstance(case,list):Div_Period = get_data('Div_Period',study,case[0])
    vall = []
    a = b = c = []
    run_case(study,case)
    if Div_Period == 6:
        if isinstance(case, int):  #### Only one case
            VolD=app.GetCurrentStudy().GetResultTable().GetData("Voltage Difference")
            a=[VolD.GetValue(i,0) for i in range(Step0,VolD.GetRows())]
            b=[VolD.GetValue(i,1) for i in range(Step0,VolD.GetRows())]
            c=[VolD.GetValue(i,2) for i in range(Step0,VolD.GetRows())]
            vall=a+[-i for i in b]+c+[-i for i in a]+b+[-i for i in c]+[a[0]]
        if isinstance(case, list):
            Step0 = Step0+1
            vall = []
            ref1 = app.GetDataManager().GetDataSet('Voltage Difference')
            app.GetDataManager().CreateAllCasesGraphModel(ref1)
            app.GetDataManager().GetGraphModel('[Cases] Voltage Difference').WriteTable(TempVAddress)
            TempVline = csvo.Loadcsv(TempVAddress)
            Rows = len(TempVline)
            for casei in case:
                a=[float(TempVline[i][(casei-1)*3+1]) for i in range(Step0,Rows)]
                b=[float(TempVline[i][(casei-1)*3+2]) for i in range(Step0,Rows)]
                c=[float(TempVline[i][(casei-1)*3+3]) for i in range(Step0,Rows)]
                v=a+[-i for i in b]+c+[-i for i in a]+b+[-i for i in c]+[a[0]]
                if vall == []: vall = v
                else: vall = [vall[i]+v[i] for i in range(len(v))]

    if Div_Period == 2:  ####Half Period
        if isinstance(case, int):
            VolD=app.GetCurrentStudy().GetResultTable().GetData("Voltage Difference")
            a=[VolD.GetValue(i,0) for i in range(Step0,VolD.GetRows())]+[VolD.GetValue(Step0,0)] ##Vlinea
            b=[VolD.GetValue(i,1) for i in range(Step0,VolD.GetRows())]+[VolD.GetValue(Step0,1)] ##Vlineb
            c=[VolD.GetValue(i,2) for i in range(Step0,VolD.GetRows())]+[VolD.GetValue(Step0,2)] ##Vlinec
            vall = [[a[i],b[i],c[i]] for i in range(len(a))]
        if isinstance(case, list):
            Step0 = Step0+1
            vall = []
            ref1 = app.GetDataManager().GetDataSet('Voltage Difference')
            app.GetDataManager().CreateAllCasesGraphModel(ref1)
            app.GetDataManager().GetGraphModel('[Cases] Voltage Difference').WriteTable(TempVAddress)
            TempVline = csvo.Loadcsv(TempVAddress)
            Rows = len(TempVline)
            for casei in case:
                a=[float(TempVline[i][(casei-1)*3+1]) for i in range(Step0,Rows)]+[-float(TempVline[i][(casei-1)*3+1]) for i in range(Step0,Rows)]+[float(TempVline[Step0][(casei-1)*3+1])] ##Vlinea
                b=[float(TempVline[i][(casei-1)*3+2]) for i in range(Step0,Rows)]+[-float(TempVline[i][(casei-1)*3+2]) for i in range(Step0,Rows)]+[float(TempVline[Step0][(casei-1)*3+2])]  ##Vlineb
                c=[float(TempVline[i][(casei-1)*3+3]) for i in range(Step0,Rows)]+[-float(TempVline[i][(casei-1)*3+3]) for i in range(Step0,Rows)]+[float(TempVline[Step0][(casei-1)*3+3])] ##Vlinec
                v = [[a[i],b[i],c[i]] for i in range(len(a))]
                if vall == []: vall = v
                else: vall = [[vall[i][0]+v[i][0],vall[i][1]+v[i][1],vall[i][2]+v[i][2]] for i in range(len(v))]

    if Div_Period == 1:  ####need to make a good use of three phase data.
        if isinstance(case, int):
            VolD=app.GetCurrentStudy().GetResultTable().GetData("Voltage Difference")
            a=[VolD.GetValue(i,0) for i in range(Step0,VolD.GetRows())]+[VolD.GetValue(Step0,0)] ##Vlinea
            b=[VolD.GetValue(i,1) for i in range(Step0,VolD.GetRows())]+[VolD.GetValue(Step0,1)] ##Vlineb
            c=[VolD.GetValue(i,2) for i in range(Step0,VolD.GetRows())]+[VolD.GetValue(Step0,2)] ##Vlinec
            vall = [[a[i],b[i],c[i]] for i in range(len(a))]
        if isinstance(case, list):
            Step0 = Step0+1
            vall = []
            ref1 = app.GetDataManager().GetDataSet('Voltage Difference')
            app.GetDataManager().CreateAllCasesGraphModel(ref1)
            app.GetDataManager().GetGraphModel('[Cases] Voltage Difference').WriteTable(TempVAddress)
            TempVline = csvo.Loadcsv(TempVAddress)
            Rows = len(TempVline)
            for casei in case:
                a=[float(TempVline[i][(casei-1)*3+1]) for i in range(Step0,Rows)]+[float(TempVline[Step0][(casei-1)*3+1])] ##Vlinea
                b=[float(TempVline[i][(casei-1)*3+2]) for i in range(Step0,Rows)]+[float(TempVline[Step0][(casei-1)*3+2])]  ##Vlineb
                c=[float(TempVline[i][(casei-1)*3+3]) for i in range(Step0,Rows)]+[float(TempVline[Step0][(casei-1)*3+3])] ##Vlinec
                v = [[a[i],b[i],c[i]] for i in range(len(a))]
                if vall == []: vall = v
                else: vall = [[vall[i][0]+v[i][0],vall[i][1]+v[i][1],vall[i][2]+v[i][2]] for i in range(len(v))]
	
    return vall

def get_Vline(study,case,Step0):
	app.SetCurrentStudy(study)
	V = get_llVoltage_Div_period(study,case,Step0)  ##V could be 1 row or multiple row(3 data set)  The length of V should be Division+1
	if isinstance(V[0], list):
		Vline = []
		for j in range(3):
			VTemp = [V[i][j] for i in range(len(V)-1)]
			Vline.append(FFT_1D_Amp(VTemp,2)[1])
		Vline = sum(Vline)/len(Vline)
	else:
		VTemp = [V[i] for i in range(len(V)-1)]
		Vline = FFT_1D_Amp(VTemp,2)[1]
	return Vline

def TV_eval(I, Deg, Tname, Iname, IAnglename, study, case, Step0):
    key = (I, Deg)
    if key in simulation_cache:
        return simulation_cache[key]
    set_para(Iname, I, study, case)
    set_para(IAnglename, Deg, study, case)
    V = round(get_Vline(study, case, Step0), 4)
    T = round(get_data(Tname, study, case), 4)
    simulation_cache[key] = (T, V)
    return T, V

def maxTfixI_noVlimit(Tname,Iname,Ivalue,IAnglename,IAngleRange,IAngleStep,study,case,Step0):
    ### This function helps to find the optimum phase angle that maximize the torque under the fixed current
    ### Method include: 1. Search in simulation cache, if already simulated, get the T and V 
    ### 2. if not simulated yet, get the simulated results on I and deg that achieves the hightest torque under each fix I, interpolate with those data, estimate the angle under that current, then check or find the T and V for the left and right angle of that estimated angle, validate if the angle is the optimum one.
    ### 3. If validate true, exit, if not, use all the data under that fix I to interpolate again, save all the simulated ones into simulation_cache.
	set_para(Iname,Ivalue,study,case)
	allData=[]#allData: 0,1,2,3: I, Deg, T, V
	Degsteps=[round(IAngleRange[0]+IAngleStep*i,4) for i in range(int((IAngleRange[1]-IAngleRange[0])/IAngleStep)+1)] # define degsteps
	doneDeg=[i[1] for i in allData]
	TodoDeg = [item for item in Degsteps if item not in doneDeg]
	outDeg=[round(IAngleRange[0]+IAngleStep*i,4) for i in[-1,(IAngleRange[1]-IAngleRange[0])/IAngleStep+1]]
	neighborDeg=[]
	last_T0 = 0
	while len(TodoDeg): 
		if len(allData)>=1:
			neighborDeg=[round(allData[0][1]+k*IAngleStep,4) for k in [-1,1]]
	
			if all([j in outDeg+doneDeg for j in neighborDeg]): #if all the neighbor points of best point now are done or out of the range, break
				TodoDeg=[]
				break
			elif neighborDeg[0] in doneDeg and neighborDeg[1] in TodoDeg :  Deg0 = neighborDeg[1] #if one of the neighbor point of the best point are not done, do this one first
			elif neighborDeg[1] in doneDeg and neighborDeg[0] in TodoDeg :  Deg0 = neighborDeg[0] #if one of the neighbor point of the best point are not done, do this one first
	
			elif len(allData)>2:
				#interpolate the data
				kindnum=2
				if len(allData)>3:kindnum=3
				fT=interpolate.interp1d([i[1] for i in allData],[i[2] for i in allData],kind=kindnum)
				fV=interpolate.interp1d([i[1] for i in allData],[i[3] for i in allData],kind=kindnum)
				Tall=fT(TodoDeg).tolist()
				Vall=fV(TodoDeg).tolist()
				DataNihe=[[Ivalue,TodoDeg[i],round(Tall[i],4),round(Vall[i],4)] for i in range(len(TodoDeg))]
				DataNihe.sort(reverse=True,key=lambda x:x[2])  #max Torque
				Deg0=DataNihe[0][1] #optimized point according to the interpolate result
				neighborDeg=[round(Deg0+k*IAngleStep,4) for k in [-1,1]] #neighbor J of J0
				neighborDeg=list(set(neighborDeg).difference(set(outDeg))) # drop off neighborDeg that outside the range
				neighborDeg.sort() #neighbor J of J0 
				for j in neighborDeg+[Deg0]: # neighborJ+[Deg0] 
					if j not in doneDeg:Deg0=j
	
	
		if Degsteps[len(Degsteps)//2] not in doneDeg:Deg0=Degsteps[len(Degsteps)//2]  #third calculate point
		if Degsteps[-1] not in doneDeg:Deg0=Degsteps[-1]   #second calculate point, 
		if Degsteps[0] not in doneDeg:Deg0=Degsteps[0]    #first calculate point
		if Deg0 == 90:
			allData.append([Ivalue,90,0,0])
			doneDeg = [i[1] for i in allData]
		if Deg0 not in doneDeg:
			set_para(IAnglename,Deg0,study,case)
			V0 = round(get_Vline(study,case,Step0),4)
			T0 = round(get_data(Tname,study,case),4)
	
			while T0==(): 
				set_para(IAnglename,Deg0,study,case)
				V0=round(get_Vline(study,case,Step0),4)
				T0 = round(get_data(Tname,study,case),4)
			allData.append([Ivalue,Deg0,T0,V0])

			# Check if the difference between new T0 and last T0 is lower than 0.01
			if last_T0 is not None and abs(T0 - last_T0) < 0.1:
				break  # Assume the max torque degree has been found
			last_T0 = T0
			allData.sort(reverse=True,key=lambda x:x[2])
			doneDeg=[i[1] for i in allData]
			TodoDeg = [item for item in Degsteps if item not in doneDeg]

	allData.sort(reverse=True,key=lambda x:x[2])
	return allData[0]

def MinIobjTfixDeg(Tname,objT,Iname,IRange,IStep,IAnglename,IAnglevalue,study,case,Step0):
	allData=[]#allData: 0,1,2,3: I, Deg, T, V
	set_para(IAnglename,IAnglevalue,study,case)
	Isteps=[round(IRange[0]+IStep*i,4) for i in range(int((max(IRange)-min(IRange))/IStep)+1)] # define degsteps
	doneI=[i[0] for i in allData]
	TodoI = [item for item in Isteps if item not in doneI]
	outI=[round(IRange[0]+IStep*i,4) for i in[-1,(IRange[1]-IRange[0])/IStep+1]]
	neighborI=[]
	while len(TodoI): 
		if len(allData)>=1:
			neighborI=[round(allData[0][0]+k*IStep,4) for k in [-1,1]]
			if all([j in outI+doneI for j in neighborI]): #if all the neighbor points of best point now are done or out of the range, break
				TodoI=[]
				break
			elif neighborI[0] in doneI and neighborI[1] in TodoI :  I0 = neighborI[1] #if one of the neighbor point of the best point are not done, do this one first
			elif neighborI[1] in doneI and neighborI[0] in TodoI :  I0 = neighborI[0] #if one of the neighbor point of the best point are not done, do this one first
	
			elif len(allData)>2:
				#interpolate the data
				kindnum=2
				if len(allData)>3:kindnum=3
				fT=interpolate.interp1d([i[0] for i in allData],[i[2] for i in allData],kind=kindnum)
				fV=interpolate.interp1d([i[0] for i in allData],[i[3] for i in allData],kind=kindnum)
				Tall=fT(TodoI).tolist()
				Vall=fV(TodoI).tolist()
				DataItp=[[TodoI[i],IAnglevalue,round(Tall[i],4),round(Vall[i],4)] for i in range(len(TodoI))]
				if max(Tall)>=objT:DataItp.sort(reverse=True,key=lambda x:(IRange[1]+10-x[0])*(x[2]>=objT))  #objT
				if max(Tall)<objT:DataItp.sort(reverse=True,key=lambda x:x[2])  #objT
				I0=DataItp[0][0] #optimized point according to the interpolate result
				neighborI=[round(I0+k*IStep,4) for k in [-1,1]] #neighbor J of J0
				neighborI=list(set(neighborI).difference(set(outI))) # drop off neighborDeg that outside the range
				neighborI.sort() #neighbor J of J0 
				for j in neighborI+[I0]: # neighborJ+[Deg0] 
					if j not in doneI:I0=j
	
		if Isteps[len(Isteps)//2] not in doneI:I0=Isteps[len(Isteps)//2]  #third calculate point
		if Isteps[-1] not in doneI:I0=Isteps[-1]   #second calculate point , 
		if Isteps[0] not in doneI:I0=Isteps[0]    #first calculate point
		if I0 == 0:
			allData.append([0,IAnglevalue,0,0])
			doneI = [i[0] for i in allData]
		if I0 not in doneI:
			set_para(Iname,I0,study,case)
			V0=round(get_Vline(study,case,Step0),4)
			T0 = round(get_data(Tname,study,case),4)
			#if app.GetCurrentStudy().GetReport().HasWarningMessage():
				#app.GetCurrentStudy().ApplyCadParameters()
	
			while T0==(): 
				set_para(Iname,I0,study,case)
				V0=round(get_Vline(study,case,Step0),4)
				T0 = round(get_data(Tname,study,case),4)
			allData.append([I0,IAnglevalue,T0,V0])
			doneT = [i[2] for i in allData]
			if max(doneT)>=objT:allData.sort(reverse=True,key=lambda x:(IRange[1]+10-x[0])*(x[2]>=objT))  #objT
			if max(doneT)<objT:allData.sort(reverse=True,key=lambda x:x[2])  #objT
			doneI=[i[0] for i in allData]
			TodoI = [item for item in Isteps if item not in doneI]
	allData.sort(reverse=True,key=lambda x:(IRange[1]+10-x[0])*(x[2]>=objT))
	return allData[0]


def predict_best_deg_from_cache(Ivalue):
    data = [(deg, t) for (i, deg), (t, _) in simulation_cache.items() if i == Ivalue]
    if len(data) < 4:
        return None
    X = np.array([deg for deg, _ in data])
    y = np.array([t for _, t in data])
    try:
        f_interp = interpolate.interp1d(X, y, kind='quadratic', fill_value='extrapolate')
    except Exception:
        f_interp = interpolate.interp1d(X, y, kind='linear', fill_value='extrapolate')
    test_degs = np.linspace(0, 180, 50)
    pred = f_interp(test_degs)
    best_idx = np.argmax(pred)
    return round(test_degs[best_idx], 2)

def predict_best_current_range(objT, IRange):
    # Extract deg vs I from cache and identify monotonicity to refine angle search
    records = [(i, deg, t) for (i, deg), (t, _) in simulation_cache.items() if IRange[0] <= i <= IRange[1]]
    if len(records) < 6:
        return None  # not enough data
    data_by_I = {}
    for i, deg, t in records:
        data_by_I.setdefault(i, []).append((deg, t))
    all_peak_degs = []
    for i in sorted(data_by_I):
        degs, torques = zip(*data_by_I[i])
        if len(degs) < 4:
            continue
        try:
            f_interp = interpolate.interp1d(degs, torques, kind='quadratic', fill_value='extrapolate')
        except Exception:
            f_interp = interpolate.interp1d(degs, torques, kind='linear', fill_value='extrapolate')
        search_degs = np.linspace(min(degs), max(degs), 50)
        pred_torque = f_interp(search_degs)
        best_deg = search_degs[np.argmax(pred_torque)]
        all_peak_degs.append(best_deg)
    if not all_peak_degs:
        return None
    return round(min(all_peak_degs), 2), round(max(all_peak_degs), 2)

def save_simulation_cache_to_csv(filename="simulation_cache.csv"):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["I", "Deg", "Torque", "Voltage"])
        for (i, deg), (t, v) in simulation_cache.items():
            writer.writerow([i, deg, t, v])

def load_simulation_cache_from_csv(filename="simulation_cache.csv"):
    try:
        with open(filename, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                i = float(row["I"])
                deg = float(row["Deg"])
                t = float(row["Torque"])
                v = float(row["Voltage"])
                simulation_cache[(i, deg)] = (t, v)
    except FileNotFoundError:
        pass

def MinI_objT_noVlimit(Tname, objT, Iname, IRange, IStep, IAnglename, IAngleRange, IAngleStep, study, case, Step0):
    """
    Find the minimum current and optimal angle to achieve target torque (objT) without considering voltage limits.
    Returns: [I, Deg, T, V] for the minimum I satisfying T >= objT
    """
    allData = []

    Ivalue = IRange[1]  # Start with max current
    IAnglevalue = IAngleRange[0]  # Start with initial angle

    # Initial set and compute
    set_para(IAnglename, IAnglevalue, study, case)
    set_para(Iname, Ivalue, study, case)
    V0 = round(get_Vline(study,case,Step0),4)
    T0 = round(get_data(Tname, study, case), 4)
    
    if T0 > objT:
        allData.append([Ivalue,IAnglevalue,T0,V0])
        # Find Imin under fixed initial angle
        Imin_IDTV = MinIobjTfixDeg(Tname, objT, Iname, IRange, IStep, IAnglename, IAnglevalue, study, case, Step0)
        Ivalue = Imin_IDTV[0]
        IRange[1] = Ivalue
        allData.append(Imin_IDTV)

        # With new Imin, find optimal angle under that current that create the maxT
        Tmax_IDTV = maxTfixI_noVlimit(Tname, Iname, Ivalue, IAnglename, IAngleRange, IAngleStep, study, case, Step0)
        IAnglevalue = Tmax_IDTV[1]
        IAngleRange[1] = IAnglevalue
        allData.append(Tmax_IDTV)
    else:
        # At max I, find best angle for max torque
        Tmax_IDTV = maxTfixI_noVlimit(Tname, Iname, Ivalue, IAnglename, IAngleRange, IAngleStep, study, case, Step0)
        if Tmax_IDTV[2] < objT:
            return None  # Target torque can't be reached
        IAnglevalue = Tmax_IDTV[1]
        IAngleRange[1] = IAnglevalue
        allData.append(Tmax_IDTV)

    # Start iterative search for better I and angle
    while True:
        prev_I = Ivalue

        # Fix angle, reduce current until just meet objT
        Imin_IDTV = MinIobjTfixDeg(Tname, objT, Iname, IRange, IStep, IAnglename, IAnglevalue, study, case, Step0)
        Ivalue = Imin_IDTV[0]
        IRange[1] = Ivalue
        allData.append(Imin_IDTV)

        if Ivalue == prev_I:
            break  # Already minimum

        # Fix new I, find better angle
        Tmax_IDTV = maxTfixI_noVlimit(Tname, Iname, Ivalue, IAnglename, IAngleRange, IAngleStep, study, case, Step0)
        IAnglevalue = Tmax_IDTV[1]
        IAngleRange[1] = IAnglevalue
        allData.append(Tmax_IDTV)

    # Sort to get lowest current that satisfies objT
    allData.sort(key=lambda x: (x[2] >= objT, x[0]))
    return allData


def MinI_objT_Vlimit(Tname,objT,Iname,IRange,IStep,IAnglename,IAngleRange,IAngleStep,Vlimit,study,case,Step0):
    load_simulation_cache_from_csv()
    # 先使用 MinI_objT_noVlimit 找到初步的解
    base_result = MinI_objT_noVlimit(Tname, objT, Iname, IRange, IStep, IAnglename, IAngleRange, IAngleStep, study, case, Step0)[0]
    if base_result is None:
        return None
    Ivalue, Deg, Tval, Vval = base_result
    
    # 如果电压已经满足限制，直接返回
    if Vval <= Vlimit:
        return base_result
    
    # 否则开始迭代调整角度和电流
    IRange = [Ivalue,IRange[1]]
    IAngleRange = [Deg,IAngleRange[1]]
        
# def MinI_objT_Vlimit(Tname,objT,Iname,IRange,IStep,IAnglename,IAngleRange,IAngleStep,Vlimit,study,case,Step0):
# 	neighborI=[]
# 	doneI = doneDeg = doneT = doneV = []
# 	allData = [] # [0]I,[1]Deg,[2]T,[3]V.
# 	IAnglevalue = IAngleRange[0]
# 	set_para(IAnglename,IAnglevalue,study,case)
# 	set_para(Iname,IRange[0],study,case)
# 	V0 = round(get_Vline(study,case,Step0),4)
# 	T0 = round(get_data(Tname,study,case),4)  
# 	
# 	if T0 < objT: #### At first test if min I can reach objT or not
# 		I0_IDTV = MinIobjTfixDeg(Tname,objT,Iname,IRange,IStep,IAnglename,IAnglevalue,study,case,Step0) #under phase0 find the minimum I to reach objT
# 		IRange = [I0_IDTV[0],IRange[1]]  #### Reduce the search range for I
# 	else: I0_IDTV = [IRange[0],IAngleRange[0],T0,V0]
# 	allData.append(I0_IDTV)

# 	Isteps=[round(IRange[0]+IStep*i,4) for i in range(int((max(IRange)-min(IRange))/IStep)+1)] # Set ISteps From min to max
# 	Degsteps=[round(IAngleRange[0]+IAngleStep*i,4) for i in range(int((IAngleRange[1]-IAngleRange[0])/IAngleStep)+1)] # define degsteps
# 	outI=[round(IRange[0]+IStep*i,4) for i in[-1,(IRange[1]-IRange[0])/IStep+1]]
# 	
# 	# 2. get data for the other two points: 
# 	InitialI = [Isteps[len(Isteps)//2],IRange[1]] #Initial three I to examine
# 	for i in range(2):
# 		Ivalue = InitialI[i]
# 		MinV_Data = MinVobjTfixI(Tname,objT,Iname,Ivalue,IAnglename,IAngleRange,IAngleStep,'DegEsti',study,case,Step0)### for the given I, find the minV 
# 		IAngleRange = [MinV_Data[1],IAngleRange[1]]  ### Update the IAngleRange, under IRange[1], 
# 		allData.append(MinV_Data)
# 	doneI = [i[0] for i in allData]
# 	TodoI = [item for item in Isteps if item not in doneI]
# 	# From now we already have 3 points, we can use 2nd function. by test 	
# 	# doneDeg can be used as a hint for the DegRange of TodoI, 1. find the position of midI in doneI, 2, get the IAngleRange from doneDeg
# 	# doneI.append(Ivalue) # The first and reference I is the largest I, which will give a hint of Vline
# 	# MinVfixI = MinVobjTfixI(Tname,objT,Iname,Ivalue,IAnglename,IAngleRange,IAngleStep,study,case)
# 	# doneV.append(MinVfixI)
# 	#set_para('ProcessNo',4,study,case) 
# 	while len(TodoI):
# 		doneI = [i[0] for i in allData]
# 		TodoI = [item for item in Isteps if item not in doneI]
# 		#objTData = [i for i in allData if i[2] >= objT]
# 		kindnum='quadratic'
# 		if len(allData)>3:kindnum='cubic'
# 		
# 		fDeg=interpolate.interp1d([i[0] for i in allData],[i[1] for i in allData],kind=kindnum) #The kind of fT should be linear since after reaching objT it becomes constant
# 		fT=interpolate.interp1d([i[0] for i in allData],[i[2] for i in allData],kind='linear') #The kind of fT should be linear since after reaching objT it becomes constant
# 		fV=interpolate.interp1d([i[0] for i in allData],[i[3] for i in allData],kind=kindnum)
# 		Degitp0 = fDeg(Isteps).tolist()
# 		TClose = lambda num,collection:min(collection,key=lambda x:abs(x-num))  ###Define a function that find the closest value in Isteps 
# 		Degitp = [TClose(Degitp0[i],Degsteps) for i in range(len(Isteps))]###Get the estimation of Deg 
# 		Titp = fT(Isteps).tolist() #get the interpolated T by using alldata, find the deg with nearest T
# 		Vitp = fV(Isteps).tolist() ###The interpolated curve will go through all the data points
# 		DataItp=[[Isteps[i],Degitp[i],round(Titp[i],4),round(Vitp[i],4)] for i in range(len(Isteps))]
# 		doneT = [i[2] for i in allData]
# 		doneV = [i[3] for i in allData]
# 		MaxI = max(IRange)

# 		if max(Titp)>=objT:DataItp.sort(reverse=True,key=lambda x:(MaxI-x[0])*(x[2]>=objT)*(x[3]<=Vlimit)-x[0]*(x[2]<objT)+(x[2]>=objT)*(Vlimit-x[3])*(x[3]>Vlimit)) #If there is esti or done T reach objT,find minI among feasible Vline
# 		else:DataItp.sort(reverse=True,key=lambda x:x[2]) #Else the target is to find the I with maxT
# 		I0=DataItp[0][0] #optimized point according to the interpolate result
# 		DegI0 = DataItp[0][1] #Deg0 is the estimated Deg to get MinV and targetT
# 		####Try I0,Deg0
# 		neighborI=[round(I0+k*IStep,4) for k in [-1,1]] #neighbor J of J0
# 		neighborI=[item for item in neighborI if item not in outI] # drop off neighborDeg that outside the range
# 		#DegneighborI = [DataItp[1][DataItp[0].index(neighborI[i])] for i in range(len(neighborI))] # find the estimated Deg to get MinV and targetT for neighborI
# 		for j in neighborI+[I0]: # neighborJ+[Deg0] 
# 			if j not in doneI:
# 				I0 = j
# 				DegI0 = Degitp[[i[0] for i in DataItp].index(I0)]
# 		#####Try I0 with DegI0 first:? or define Deg0 in MinVobjTfixI, give a good guess on deg
# 		
# 		if all([j in doneI+outI for j in neighborI]):
# 				TodoI=[]
# 				break
# 		####for those I that can reach objT,larger I has smaller Deg to reach objT#####
# 	#####Find out all the doneData that can reach objT######
# 		#objTData = [i for i in allData if i[2] >= objT]
# 		if I0 not in doneI:
# 			index_doneI_left = doneI.index(max(doneI,key = lambda x:I0/(I0-x)))
# 			index_doneI_right = doneI.index(max(doneI,key = lambda x:I0/(x-I0))) #The index of near right I in doneI for Ivalue
# 			doneDeg = [i[1] for i in allData]
# 			IAngleRange0 = [doneDeg[index_doneI_right],doneDeg[index_doneI_left]]
# 			IAngleRange0.sort()
# 			if DegI0 >= IAngleRange0[1] or DegI0 <= IAngleRange0[0]: DegI0 = 'DegEsti'
# 			MinV_Data = MinVobjTfixI(Tname,objT,Iname,I0,IAnglename,IAngleRange0,IAngleStep,DegI0,study,case,Step0)
# 			allData.append(MinV_Data)
# 			allData.sort(reverse=True,key=lambda x:(MaxI-x[0])*(x[2]>=objT)*(x[3]<=Vlimit)-x[0]*(x[2]<objT)+(x[2]>=objT)*(Vlimit-x[3])*(x[3]>Vlimit)) 
# 	return (allData)


def objTfixI_Airgap(Tname,objT,Iname,Ivalue,Airgapname,AirgapRange,AirgapStep,study,case,Step0):
	IAngleRange = AirgapRange
	IAnglename = Airgapname
	IAngleStep = AirgapStep

	set_para(Iname,Ivalue,study,case)
	
	allData=[]#allData: 0,1,2,3: I, Deg, T, V
	Degsteps=[round(IAngleRange[0]+IAngleStep*i,4) for i in range(int((IAngleRange[1]-IAngleRange[0])/IAngleStep)+1)] # define degsteps
	doneDeg=[i[1] for i in allData]
	TodoDeg = [item for item in Degsteps if item not in doneDeg]
	outDeg=[round(IAngleRange[0]+IAngleStep*i,4) for i in[-1,(IAngleRange[1]-IAngleRange[0])/IAngleStep+1]]
	neighborDeg=[]

	while len(TodoDeg): 
		if len(allData)>=1:
			neighborDeg=[round(allData[0][1]+k*IAngleStep,4) for k in [-1,1]]
	
			if all([j in outDeg+doneDeg for j in neighborDeg]): #if all the neighbor points of best point now are done or out of the range, break
				TodoDeg=[]
				break
			elif neighborDeg[0] in doneDeg and neighborDeg[1] in TodoDeg :  Deg0 = neighborDeg[1] #if one of the neighbor point of the best point are not done, do this one first
			elif neighborDeg[1] in doneDeg and neighborDeg[0] in TodoDeg :  Deg0 = neighborDeg[0] #if one of the neighbor point of the best point are not done, do this one first
	
			elif len(allData)>2:
				#interpolate the data
				kindnum=2
				if len(allData)>3:kindnum=3
				fT=interpolate.interp1d([i[1] for i in allData],[i[2] for i in allData],kind=kindnum)
				fV=interpolate.interp1d([i[1] for i in allData],[i[3] for i in allData],kind=kindnum)
				Tall=fT(TodoDeg).tolist()
				Vall=fV(TodoDeg).tolist()
				DataNihe=[[Ivalue,TodoDeg[i],round(Tall[i],4),round(Vall[i],4)] for i in range(len(TodoDeg))]
				DataNihe.sort(reverse=True,key=lambda x:objT/(x[2]-objT))  #max Torque
				Deg0=DataNihe[0][1] #optimized point according to the interpolate result
				neighborDeg=[round(Deg0+k*IAngleStep,4) for k in [-1,1]] #neighbor J of J0
				neighborDeg=list(set(neighborDeg).difference(set(outDeg))) # drop off neighborDeg that outside the range
				neighborDeg.sort() #neighbor J of J0 
				for j in neighborDeg+[Deg0]: # neighborJ+[Deg0] 
					if j not in doneDeg:Deg0=j
	
	
		if Degsteps[len(Degsteps)//2] not in doneDeg:Deg0=Degsteps[len(Degsteps)//2]  #third calculate point
		if Degsteps[-1] not in doneDeg:Deg0=Degsteps[-1]   #second calculate point , 
		if Degsteps[0] not in doneDeg:Deg0=Degsteps[0]    #first calculate point
		if Deg0 == 90:
			allData.append([Ivalue,90,0,0])
			doneDeg = [i[1] for i in allData]
		if Deg0 not in doneDeg:
			set_para(IAnglename,Deg0,study,case)
			app.GetModel(model).GetStudy(study).DeleteMeshAllCases()
			V0=round(get_Vline(study,case,Step0),4)
			T0 = round(get_data(Tname,study,case),4)
			

			#if app.GetCurrentStudy().GetReport().HasWarningMessage():
				#app.GetCurrentStudy().ApplyCadParameters()
	
			while T0==(): 
				set_para(IAnglename,Deg0,study,case)
				app.GetModel(model).GetStudy(study).DeleteMeshAllCases()
				V0=round(get_Vline(study,case,Step0),4)
				T0 = round(get_data(Tname,study,case),4)
			allData.append([Ivalue,Deg0,T0,V0])
	
			allData.sort(reverse=True,key=lambda x:x[2])
			doneDeg=[i[1] for i in allData]
			TodoDeg = [item for item in Degsteps if item not in doneDeg]

	allData.sort(reverse=True,key=lambda x:objT/(x[2]-objT))
	
	return allData

def set_inslot_dimensions(study, case, inslot_para):
    set_para('Radial_Clearence', inslot_para.Radial_Clearence, study, case)
    set_para('Side_Clearence', inslot_para.Side_Clearence, study, case)
    set_para('Wire_Coating_Thickness', inslot_para.Wire_Coating_Thickness, study, case)
    set_para('Insulation_Thickness', inslot_para.Insulation_Thickness, study, case)
    set_para('Wire_Gap', inslot_para.Wire_Gap, study, case)
        
def Full_Stator_Assignment(Stator_Para,Inslot_Para,Winding_Para,Model_Para,EW_info,cond_info,results, materialname = 'Copper_152C',numlayer_name = 'Conductor_Layer'):
    study = Model_Para.study
    case = Model_Para.case   
    set_stator_by_ratio(study,case,Stator_Para,Winding_Para)
    set_inslot_dimensions(study, case, Inslot_Para)
    Winding_Cond_Assignment(Winding_Para,Model_Para,cond_info,materialname,numlayer_name)
    Process_conductor_layer_settings(Winding_Para,Model_Para)
    Coil_EndWinding_Setting(Winding_Para,Model_Para,Stator_Para,Inslot_Para,EW_info,results)
    
def Winding_Cond_Assignment(Winding_Para,Model_Para,cond_info,materialname = 'Copper_152C',numlayer_name = 'Conductor_Layer'):
#This function is to assign the Winding Parameter to the machine.The parameters include the number of layers, (after assigning the number of layers, the material of winding needs to be assigned as well), if variable cross section and hybrid material are selected, vcs or hym = 1, then require for the matrix to give the material of each layer and the thickness ratio and tangential layer number of each radial layer.
    study = Model_Para.study
    case = Model_Para.case       
    app,model,mstudy,result = initialize_jmag()        
    MODEL_DIVISION = Model_Para.MODEL_DIVISION
    num_slots = Winding_Para.num_slots
    num_layers = Winding_Para.num_layers
    num_phases = Winding_Para.num_phases
    num_poles = Winding_Para.num_poles
    q = Winding_Para.q
    if model.IsCadLinkOpen() == False:model.RestoreCadLink()
    app.SetCurrentStudy(study)
    set_para(numlayer_name,num_layers,study,case)
    set_para('MODEL_DIVISION',MODEL_DIVISION,study,case)
    model.GetGroupList().RemoveAllGroups()
    Cond_Radial_Interval = get_data('Cond_Radial_Interval',study,case)
    layer_nb = num_layers
    Gcx = np.zeros((num_slots, layer_nb))
    Gcy = np.zeros((num_slots, layer_nb))
    Gcz = np.zeros((num_slots, layer_nb))
    R2 = get_data('SD2',study,case)/2  # base of slot opening
    cond_distance_tooth_L = get_data('ST',study,case)  # distance between conductor and slot opening
    R_cond = R2 + cond_distance_tooth_L    # reference radius for conductors inside the slot
    alpha = 2*np.pi/(2*num_slots)
    sel = mstudy.GetMeshControl().GetCondition(u"Coil").GetSelection()
    sel2 = mstudy.GetMeshControl().GetCondition(u"Skin").GetSelection()
    for slot in range(0,int(num_slots/MODEL_DIVISION)):
        alpha_cond = (1 + (slot)*2) * alpha
        for layer in range(0,layer_nb):  # Notice the Python indexes start from 0
            Cond_radius = (R_cond + ((layer_nb-layer-1)*Cond_Radial_Interval))
            Gcx[slot, layer] = Cond_radius * np.cos(alpha_cond)
            Gcy[slot, layer] = Cond_radius * np.sin(alpha_cond)
            Gcz[slot, layer] = 0
            coil_name = 'S'+str(slot)+'L'+str(layer)
            P1 = app.CreatePoint(Gcx[slot,layer],Gcy[slot,layer],Gcz[slot,layer])
            part_1 = model.GetPartByPosition(P1)
            if part_1.GetName() != coil_name:
                part_1.SetName(coil_name)
                part_1.SetColor('yellow')
            if model.GetStudy(study).GetMaterial(coil_name) != materialname:           
                model.GetStudy(study).SetMaterialByName(coil_name, materialname)
                model.GetStudy(study).GetMaterial(coil_name).SetValue(u"EddyCurrentCalculation", 1)
                model.GetStudy(study).GetMaterial(coil_name).SetValue(u"UserConductivityType", 0)
            #model.GetStudy(study).GetMaterial(coil_name).SetValue(u"Laminated", 0)
            sel.SelectPart(coil_name)
            sel2.SelectPart(coil_name)
    mstudy.GetMeshControl().GetCondition(u"Coil").ClearParts()
    mstudy.GetMeshControl().GetCondition(u"Coil").AddSelected(sel)
    mstudy.GetMeshControl().GetCondition(u"Skin").ClearParts()
    mstudy.GetMeshControl().GetCondition(u"Skin").AddSelected(sel2)
####If MODEL_DIVISION > 1, which means it is a period model, assign the FEM conductor Circuit
    if MODEL_DIVISION > 1:####If this is an period model. 
        #app.Load(u"D:/CumminsMachine/[BaseReference_48-8]_Period_Model.jproj")
        # if num_phases == 3:######################################################################################
        #     mstudy.LoadCircuit(u"Standard_Circuit_3_Phase.jcir")
        ##Add FEM conductors to the condition, create FEMConductor for Phases
        Phase_Conds = [0] * num_phases
        for i in range(num_phases):
            PhaseName = 'Phase'+ str(get_phase_code(i+1))  ### Turn the 0 1 2 into 'A' 'B' 'C'
            mstudy.DeleteCondition(PhaseName)
            mstudy.CreateCondition(u"FEMConductor", PhaseName)
            Condition = mstudy.GetCondition(PhaseName)
            Condition.SetLink(PhaseName+'Cond')
            ###This is for the first subcondition, set the name as identical to conductor name format S1L1
            #mstudy.GetCondition(PhaseName).GetSubCondition(u"untitled").SetName(u"Cond1")
        for slot in range(int(num_slots/MODEL_DIVISION)):
            for layer in range(num_layers):
                Phase_Index = get_phase_index(slot, layer, cond_info)
                PhaseName = 'Phase'+ str(get_phase_code(Phase_Index+1))
                Condition = mstudy.GetCondition(PhaseName)
                Cond_name = 'S'+str(slot)+'L'+str(layer)
                if Phase_Conds[Phase_Index] == 0:
                    Condition.GetSubCondition(u"untitled").SetName(Cond_name)
                else: 
                    Condition.CreateSubCondition(u"FEMConductorData", Cond_name)
                sel = Condition.GetSubCondition(Cond_name).GetSelection()
                sel.SelectPart(Cond_name)
                mstudy.GetCondition(PhaseName).GetSubCondition(Cond_name).AddSelected(sel)
                direction = -1 if Phase_Index % 2 == 0 else 1
                if MODEL_DIVISION == num_poles and slot > q and Phase_Index == 0:
                    direction = - direction
                Condition.GetSubCondition(Cond_name).SetValue("Direction2D", direction)
                Phase_Conds[Phase_Index] += 1
            ### Get the phaseIndex for each conductor, Based on the q, the layer, the phase shift feature, 

    if MODEL_DIVISION == 1: ####If this is a full Model. 
        #app.Load(u"D:/CumminsMachine/[BaseReference_48-8]_Full_Model.jproj")
        #if num_phases == 3:######################################################################################
            #mstudy.LoadCircuit(u"D:/CumminsMachine/Standard_Circuit_3_Phase.jcir")
        ##Add FEM conductors to the condition, create FEMConductor for Phases
        Phase_Conds = [0] * num_phases
        for i in range(num_phases):
            PhaseName = 'Phase'+ str(get_phase_code(i+1))  ### Turn the 0 1 2 into 'A' 'B' 'C'
            mstudy.DeleteCondition(PhaseName)
            mstudy.CreateCondition(u"FEMConductor", PhaseName)
            Condition = mstudy.GetCondition(PhaseName)
            Condition.SetLink(PhaseName+'Cond')
            ###This is for the first subcondition, set the name as identical to conductor name format S1L1
            #mstudy.GetCondition(PhaseName).GetSubCondition(u"untitled").SetName(u"Cond1")
        for slot in range(int(num_slots/MODEL_DIVISION)):
            for layer in range(num_layers):
                Phase_Index = get_phase_index(slot, layer, cond_info)
                PhaseName = 'Phase'+ str(get_phase_code(Phase_Index+1))
                Condition = mstudy.GetCondition(PhaseName)
                Cond_name = 'S'+str(slot)+'L'+str(layer)
                pole_index = get_pole_index(slot, layer, cond_info)
                if Phase_Conds[Phase_Index] == 0:
                    Condition.GetSubCondition(u"untitled").SetName(Cond_name)
                else: 
                    Condition.CreateSubCondition(u"FEMConductorData", Cond_name)
                sel = Condition.GetSubCondition(Cond_name).GetSelection()
                sel.SelectPart(Cond_name)
                mstudy.GetCondition(PhaseName).GetSubCondition(Cond_name).AddSelected(sel)
                direction = -1 if Phase_Index % 2 == 0 else 1   ##### A C B 
                if MODEL_DIVISION == num_poles and slot > q and Phase_Index == 0:
                    direction = - direction
                if int(pole_index) % 2 == 1:  ### Reverse the direction of current based on Pole region (N +1, S -1)
                    direction = - direction
                # print (pole_index)
                Condition.GetSubCondition(Cond_name).SetValue("Direction2D", direction)
                Phase_Conds[Phase_Index] += 1

def Group_conductor_by_layer(study,case,Winding_Para,Model_Para):
    app,model,mstudy,result = initialize_jmag()
    max_layer_number = 16
    for layer in range(max_layer_number):
        layername = 'Layer'+str(layer)
        model.GetGroupList().RemoveGroup(layername)
    for layer in range(Winding_Para.num_layers):
        layername = 'Layer'+str(layer)
        model.GetGroupList().CreateGroup(layername)
        for slot in range(int(Winding_Para.num_slots/Model_Para.MODEL_DIVISION)):
            model.GetGroupList().AddPartToGroup('Layer'+str(layer),'S'+str(slot)+'L'+str(layer))
        mstudy.GetMaterial(layername).SetValue(u"UserConductivityType", 2)
        mstudy.GetMaterial(layername).SetValue(u"UserResistivityValue", u"Curesistivity_Eff")

def set_stator_by_ratio(study,case,Stator_Para,Winding_Para):
    slot_pitch = Stator_Para.SD2*math.pi/Winding_Para.num_slots
    SW3 = round(slot_pitch * Stator_Para.ksw,3)
    Wso = round(slot_pitch * Stator_Para.kso,3)
    set_para('SW3',SW3,study,case)
    set_para('Wso',Wso,study,case)
    set_para('Parallel_Branch',Winding_Para.ab,study,case)
    set_para('SLOTS',Winding_Para.num_slots,study,case)
            
def Add_AreCond_measurement_by_layer(Winding_Para):
    app,model,mstudy,result = initialize_jmag()
    for layer in range(Winding_Para.num_layers):
        Area_name = 'AreaCond_L'+str(layer)
        mstudy.GetDesignTable().RemoveMeasurementVariable(Area_name)
        mstudy.GetDesignTable().AddMeasurementVariable(Area_name)
        mstudy.GetDesignTable().GetMeasurementVariable(Area_name).ClearParts()
        sel = mstudy.GetDesignTable().GetMeasurementVariable(Area_name).GetSelection()
        sel.SelectPart('S1L'+str(layer))
        mstudy.GetDesignTable().GetMeasurementVariable(Area_name).AddSelected(sel)
        mstudy.GetOptimizationTable().AddExpressionItem(Area_name)
        mstudy.GetOptimizationTable().GetExpressionItem(Area_name).SetExpression(Area_name)
        DesignTable = mstudy.GetDesignTable()
        #DesignTable.RemoveEquation(u"AreaCond")
        #DesignTable.AddEquation(u"AreaCond")
        Equation = DesignTable.GetEquation(u"AreaCond")
        Equation.SetType(1)
        Cond_terms = ['AreaCond_L{}'.format(i) for i in range(Winding_Para.num_layers)]
        expression = '+'.join(Cond_terms)
        Equation.SetExpression(expression)
    mstudy.ApplyCadParameters()
    
def Process_conductor_layer_settings(Winding_Para,Model_Para):
    study = Model_Para.study
    case = Model_Para.case  
    app,model,mstudy,result = initialize_jmag()
    max_layer_number = 16
#####Delete the former settings
    for layer in range(max_layer_number):
        Area_name = 'AreaCond_L'+str(layer)    
        mstudy.GetDesignTable().RemoveMeasurementVariable(Area_name)
        mstudy.GetOptimizationTable().RemoveExpressionItem(Area_name)
        mstudy.DeleteParametricData('CopperLoss_Layer'+str(layer))
    Add_AreCond_measurement_by_layer(Winding_Para)
    Group_conductor_by_layer(study,case,Winding_Para,Model_Para)
    Add_LayerCopperLossResponseData(study,case,Winding_Para)
        
def Add_LayerCopperLossResponseData(study,case,Winding_Para):
    app,model,mstudy,result = initialize_jmag()
    for layer in range(Winding_Para.num_layers):
        layername = 'Layer'+str(layer)
        parameter = app.CreateResponseDataParameter('CopperLoss_'+layername)
        parameter.SetCalculationType('RMS')
        parameter.SetUnit('Step')
        parameter.SetRangeFromLastStep(u"Num_Steps-Step0")
        parameter.SetAllLine(False)
        parameter.SetCaseRangeType(3)
        parameter.SetVariable('CopperLoss_'+layername)
        parameter.SetLine(layername)
        mstudy.CreateParametricDataFromTable(u"Joule Loss", parameter)
    copper_loss_terms = ['CopperLoss_Layer{}'.format(i) for i in range(Winding_Para.num_layers)]
    expression = '+'.join(copper_loss_terms)
    mstudy.GetOptimizationTable().RemoveExpressionItem(u"ActiveCopperLoss")
    mstudy.GetOptimizationTable().AddExpressionItem(u"ActiveCopperLoss")
    mstudy.GetOptimizationTable().GetExpressionItem(u"ActiveCopperLoss").SetExpression(expression)
    mstudy.GetOptimizationTable().GetExpressionItem(u"ActiveCopperLoss").SetIsExpression(1)
    mstudy.GetOptimizationTable().GetExpressionItem(u"ActiveCopperLoss").SetTitle(u"ActiveCopperLoss")
    
def Set_Phase_A_sub_Conductors(Winding_Para,Model_Para,cond_info):
    app,model,mstudy,result = initialize_jmag()
    q, num_poles, num_layers, num_phases, num_slots, ab = Winding_Para
    MODEL_DIVISION = Model_Para.MODEL_DIVISION
    mstudy.LoadCircuit(u"Standard_Circuit_3_Phase_EndWinding_PhaseA_Sub.jcir")
    num_cond_per_phase = q * num_poles *num_layers / Model_Para.MODEL_DIVISION
    mstudy.GetCircuit().DeleteInstance(u"Serial Conductors1", 0)
    circuit = mstudy.GetCircuit().CreateDynamicCircuit(u"Serial-Conductors")
    circuit.SetValue(u"Conductors", num_cond_per_phase)
    circuit.SetValue(u"GroupCondition", False)
    circuit.Submit(u"Serial Conductors1", -24, 12)  #### Put the serial-Conductors into right position.
    PhaseName = 'PhaseA'
    mstudy.DeleteCondition(PhaseName)
    Cond_Index = 0
    for slot in range(int(num_slots/MODEL_DIVISION)):
        for layer in range(num_layers):
            Cond_name = 'S'+str(slot)+'L'+str(layer)
            Phase_Index = get_phase_index(slot, layer, cond_info)
            if Phase_Index == 0:
                Cond_Index += 1 
                Cond_name = 'S'+str(slot)+'L'+str(layer)
                mstudy.DeleteCondition(Cond_name)
                mstudy.CreateCondition(u"FEMConductor", Cond_name)
                Condition = mstudy.GetCondition(Cond_name)
                Condition.GetSubCondition(u"untitled").SetName(Cond_name)
                sel = Condition.GetSubCondition(Cond_name).GetSelection()
                sel.SelectPart(Cond_name)
                Condition.GetSubCondition(Cond_name).AddSelected(sel)
                Condition.SetLink('Conductor '+ str(Cond_Index))
                direction = -1 if Phase_Index % 2 == 0 else 1
                if MODEL_DIVISION == num_poles and slot > q and Phase_Index == 0:
                    direction = - direction
                Condition.GetSubCondition(Cond_name).SetValue("Direction2D", direction)
    for i in range(1,num_phases):
        PhaseName = 'Phase'+ str(get_phase_code(i+1))  ### Turn the 0 1 2 into 'A' 'B' 'C'
        Condition = mstudy.GetCondition(PhaseName)
        Condition.SetLink(PhaseName+'Cond')
        mstudy.DeleteCondition('PM')

def Set_Phase_A_Frequency_Analysis():
    app,model,mstudy,result = initialize_jmag()
    Step = 1
    Start_Freq = 1000
    Frequency_Step = 1000
    mstudy.GetStep().SetValue('Step', Step)
    mstudy.GetStep().SetValue(u"StepType", 0)
    mstudy.GetStep().SetValue('FrequencyStep', Frequency_Step)
    mstudy.GetStep().SetValue('Initialfrequency', Start_Freq)
    
def Coil_EndWinding_Setting(Winding_Para,Model_Para,Stator_Para,Inslot_Para,EW_info,results):
    app,model,mstudy,result = initialize_jmag()
    ## A set coil with end winding inductance and resistance, and magnet.
    q, num_poles, num_layers, num_phases, num_slots, ab = Winding_Para
    study = Model_Para.study
    case = Model_Para.case
    ##### Get the phase end winding parameters
    R_PhaseEndW, L_PhaseEndW, PhaseEndW_Length = end_winding_calc.calculate_phase_parameters_by_results(Winding_Para,Model_Para,Stator_Para,Inslot_Para,EW_info,results)
    # print ('PhaseEndW_Length = ',PhaseEndW_Length)
    set_para('End_Resistance',R_PhaseEndW,study,case)
    set_para('End_Leakage_Inductance',L_PhaseEndW,study,case)
    
    return (R_PhaseEndW,L_PhaseEndW,PhaseEndW_Length)

def Coil_EndWinding_and_Magnet_Loss_Setting(Winding_Para,Model_Para,Stator_Para,Inslot_Para,EW_info,results):
    app,model,mstudy,result = initialize_jmag()
    ## A set coil with end winding inductance and resistance, and magnet.
    q, num_poles, num_layers, num_phases, num_slots, ab = Winding_Para
    study = Model_Para.study
    case = Model_Para.case
    phase_names = ['Phase' + chr(ord('A') + i) for i in range(num_phases)]
    for phase in phase_names:
        mstudy.GetCondition(phase).SetLink(u"{}Cond".format(phase))
    #### Set magnet
    mstudy.DeleteCondition(u"PM")
    mstudy.CreateCondition(u"FEMConductor", u"PM")
    mstudy.GetCondition(u"PM").SetLink(u"PM")
    Condition = mstudy.GetCondition(u"PM")
    magnet_names = ['Magnet' + str(i+1) for i in range(6)]
    for magnet in magnet_names:
        mstudy.GetMaterial(magnet).SetValue(u"EddyCurrentCalculation", 1)
        mstudy.GetMaterial(magnet).SetValue(u"SetInsulationFlag", 1)
        Condition.CreateSubCondition(u"FEMConductorData", magnet)
        Condition.GetSubCondition(magnet).AddPart(magnet)
    Condition.RemoveSubCondition(u"untitled")
    ##### Get the phase end winding parameters
    R_PhaseEndW, L_PhaseEndW, PhaseEndW_Length = end_winding_calc.calculate_phase_parameters_by_results(Winding_Para,Model_Para,Stator_Para,Inslot_Para,EW_info,results)
    set_para('End_Resistance',R_PhaseEndW,study,case)
    set_para('End_Leakage_Inductance',L_PhaseEndW,study,case)
    
def initilize_para(Model_Para,ksw,kso,q,num_poles,num_layers,num_phases,num_slots,ab):
    study = Model_Para.study
    case = Model_Para.case
    # Standard library imports
    from collections import namedtuple
    
    num_slots = int(num_poles*num_phases*q)
    set_para('SLOTS',num_slots,study,case)
    set_para('Conductor_Layer',num_layers,study,case)
    data_names = ['StackLength','SD1','SD2']
    Stack_length,SD1,SD2 = get_datas(data_names,study,case)
    slot_pitch = SD2*math.pi/num_slots
    SW3 = round(slot_pitch * ksw,3)
    Wso = round(slot_pitch * kso,3)
    set_para('SW3',SW3,study,case)
    set_para('Wso',Wso,study,case)
    set_para('Parallel_Branch', ab, study, case)
    Curesistivity_Eff = 2.5364e-08
    
    data_names = ['StackLength','SD1','SD2','SW4','Cond_Height','Cond_Width','TH1','TH2','Wire_Gap','Side_Clearence','Radial_Clearence','Insulation_Thickness','Overlap_Ins','Wire_Coating_Thickness','Cond_Radi'] 

    Stack_length,SD1,SD2, H_yoke, H_cond, W_cond, TH1, TH2, G_cond,C_side,C_rad,d_Ins,Overlap_Ins,d_coat,Cond_Radi= get_datas(data_names,study,case)

    StatorParaGroup = namedtuple('StatorPara', ['StackLength','SD1', 'SD2', 'Hyoke', 'TH1', 'TH2','ksw','kso'])
    Stator_Para = StatorParaGroup(Stack_length,SD1, SD2, H_yoke, TH1, TH2, ksw, kso)

    WindingParaGroup = namedtuple('WindingPara', ['q', 'num_poles', 'num_layers', 'num_phases', 'num_slots', 'ab'])
    Winding_Para = WindingParaGroup(q, num_poles, num_layers, num_phases, num_slots, ab)

    set_stator_by_ratio(study,case,Stator_Para,Winding_Para)

    InslotParaGroup = namedtuple('InslotPara', ['Cond_Height', 'Cond_Width', 'Wire_Gap', 'Cond_Radi','Radial_Clearence', 'Side_Clearence', 'Wire_Coating_Thickness', 'Insulation_Thickness','Curesistivity_Eff'])
    Inslot_Para = InslotParaGroup(H_cond,W_cond,G_cond,Cond_Radi,C_rad, C_side, d_coat, d_Ins,Curesistivity_Eff)
    
    return (Stator_Para,Winding_Para,Inslot_Para)
    
    
def maxTfixI_Vlimit(Tname,Vlimit,Iname,Ivalue,IAnglename,IAngleRange,IAngleStep,study,case,Step0):
	set_para(Iname,Ivalue,study,case)
	allData=[]#allData: 0,1,2,3: I, Deg, T, V
	Degsteps=[round(IAngleRange[0]+IAngleStep*i,4) for i in range(int((IAngleRange[1]-IAngleRange[0])/IAngleStep)+1)] # define degsteps
	doneDeg=[i[1] for i in allData]
	TodoDeg = [item for item in Degsteps if item not in doneDeg]
	outDeg=[round(IAngleRange[0]+IAngleStep*i,4) for i in[-1,(IAngleRange[1]-IAngleRange[0])/IAngleStep+1]]
	neighborDeg=[]

	while len(TodoDeg): 
		if len(allData)>=1:
			neighborDeg=[round(allData[0][1]+k*IAngleStep,4) for k in [-1,1]]
	
			if all([j in outDeg+doneDeg for j in neighborDeg]): #if all the neighbor points of best point now are done or out of the range, break
				TodoDeg=[]
				break
			elif neighborDeg[0] in doneDeg and neighborDeg[1] in TodoDeg :  Deg0 = neighborDeg[1] #if one of the neighbor point of the best point are not done, do this one first
			elif neighborDeg[1] in doneDeg and neighborDeg[0] in TodoDeg :  Deg0 = neighborDeg[0] #if one of the neighbor point of the best point are not done, do this one first
	
			elif len(allData)>2:
				#interpolate the data
				kindnum=2
				if len(allData)>3:kindnum=3
				fT=interpolate.interp1d([i[1] for i in allData],[i[2] for i in allData],kind=kindnum)
				fV=interpolate.interp1d([i[1] for i in allData],[i[3] for i in allData],kind=kindnum)
				Tall=fT(TodoDeg).tolist()
				Vall=fV(TodoDeg).tolist()
				DataNihe=[[Ivalue,TodoDeg[i],round(Tall[i],4),round(Vall[i],4)] for i in range(len(TodoDeg))]
				DataNihe.sort(reverse=True,key=lambda x:x[2]*(x[3]<=Vlimit)-x[3]*(x[3]>Vlimit)) #max Torque under Vlimit
				Deg0=DataNihe[0][1] #optimized point according to the interpolate result
				neighborDeg=[round(Deg0+k*IAngleStep,4) for k in [-1,1]] #neighbor J of J0
				neighborDeg=list(set(neighborDeg).difference(set(outDeg))) # drop off neighborDeg that outside the range
				neighborDeg.sort() #neighbor J of J0 
				for j in neighborDeg+[Deg0]: # neighborJ+[Deg0] 
					if j not in doneDeg:Deg0=j
		if Degsteps[len(Degsteps)//2] not in doneDeg:Deg0=Degsteps[len(Degsteps)//2]  #third calculate point
		if Degsteps[-1] not in doneDeg:Deg0=Degsteps[-1]   #second calculate point , 
		if Degsteps[0] not in doneDeg:Deg0=Degsteps[0]    #first calculate point
		if Deg0 == 90:
			allData.append([Ivalue,90,0,0])
			doneDeg = [i[1] for i in allData]
		if Deg0 not in doneDeg:
			set_para(IAnglename,Deg0,study,case)
			V0=round(get_Vline(study,case,Step0),4)
			T0 = round(get_data(Tname,study,case),4)
			#if app.GetCurrentStudy().GetReport().HasWarningMessage():
				#app.GetCurrentStudy().ApplyCadParameters()
	
			while T0==(): 
				set_para(IAnglename,Deg0,study,case)
				V0=round(get_Vline(study,case,Step0),4)
				T0 = round(get_data(Tname,study,case),4)
			allData.append([Ivalue,Deg0,T0,V0])
	
			allData.sort(reverse=True,key=lambda x:x[2]*(x[3]<=Vlimit)-x[3]*(x[3]>Vlimit)) ###if < Vlimit return T, if > Vlimit return -Vline.
			doneDeg=[i[1] for i in allData]
			TodoDeg = [item for item in Degsteps if item not in doneDeg]
	return allData[0]
