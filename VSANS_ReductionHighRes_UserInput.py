import numpy as np
import h5py
import scipy as sp
from scipy.optimize.minpack import curve_fit
import matplotlib.pyplot as plt
from pathlib import Path
import dateutil
import datetime
from numpy.linalg import inv
#from uncertainties import unumpy
import os
import os.path
from UserInput import *

'''
Note about User-Defined Masks (which are added in additiona to the detector shadowing already accounted for):
Must be in form #####_VSANS_TRANS_MASK.h5, #####_VSANS_SOLENOID_MASK.h5, or #####_VSANS_NOSOLENOID_MASK.h5, where ##### is the assocated filenumber and
the data with that filenumber must be in the data folder (used to match configurations). These masks can be made using IGOR.
'''

#*************************************************
#***        Definitions, Functions             ***
#*************************************************

all_detectors = ["B", "MT", "MB", "MR", "ML", "FT", "FB", "FR", "FL"]
short_detectors = ["MT", "MB", "MR", "ML", "FT", "FB", "FR", "FL"]
file_objects = {}

def get_by_filenumber(filenumber, cache=True):
    if filenumber in file_objects:
        return file_objects[filenumber]
    else:
        filename = "sans" + str(filenumber) + ".nxs.ngv"
        fullpath = os.path.join(input_path, filename)
        if os.path.isfile(fullpath):
            file_object = h5py.File(fullpath)
            file_objects[filenumber] = file_object
            return file_object
        else:
            return None

def VSANS_Config_ID(filenumber):
    f = get_by_filenumber(filenumber)
    if f is not None:
        Desired_FrontCarriage_Distance = int(f['entry/DAS_logs/carriage1Trans/desiredSoftPosition'][0]) #in cm
        Desired_MiddleCarriage_Distance = int(f['entry/DAS_logs/carriage2Trans/desiredSoftPosition'][0]) #in cm
        WV = str(f['entry/DAS_logs/wavelength/wavelength'][0])
        Wavelength = WV[:3]
        GuideHolder = f['entry/DAS_logs/guide/guide'][0]
        if "CONV" in str(GuideHolder):
            Guides =  "CvB"
        else:
            GuideNum = int(f['entry/DAS_logs/guide/guide'][0])
            Guides = str(GuideNum) 
        Configuration_ID = str(Guides) + "Gd" + str(Desired_FrontCarriage_Distance) + "cmF" + str(Desired_MiddleCarriage_Distance) + "cmM" + str(Wavelength) + "Ang"
    return Configuration_ID

def VSANS_File_Type(filenumber):
    Type = 'UNKNOWN'
    SolenoidPosition = 'UNKNOWN'    
    f = get_by_filenumber(filenumber)
    if f is not None:
        Purpose = f['entry/reduction/file_purpose'][()]
        '''Purpose means SCATT, TRANS, HE3'''
        if str(Purpose).find("SCATT") != -1:
            Type = 'SCATT'
        else:
            Type = 'TRANS'
        if "backPolarization" in f['entry/DAS_logs/']:
            BackPolDirection = f['entry/DAS_logs/backPolarization/direction'][()]
        else:
            BackPolDirection = [b'UNPOLARIZED']
        if str(BackPolDirection).find("UP") != -1 or str(BackPolDirection).find("DOWN") != -1:
            SolenoidPosition = 'IN'
        else:
            SolenoidPosition = 'OUT'
            
    return Type, SolenoidPosition

def VSANS_SortDataAutomatic(YesNoManualHe3Entry, New_HE3_Files, MuValues, TeValues):
    BlockBeam = {}
    Configs = {}
    Sample_Names = {}
    Sample_Bases = {}
    Scatt = {}
    Trans = {}
    Pol_Trans = {}
    HE3_Trans = {}
    FileNumberList = [0]
    UU_filenumber = -10
    DU_filenumber = -10
    DD_filenumber = -10
    UD_filenumber = -10
    filenames = '0'
    record_adam4021 = 0
    record_temp = 0
    CellIdentifier = 0
    HE3OUT_filenumber = -10
    start_number = 0
    filelist = [fn for fn in os.listdir(input_path) if fn.endswith(".nxs.ngv")] #or filenames = [fn for fn in os.listdir("./") if os.path.isfile(fn)]
    filelist.sort()
    if len(filelist) >= 1:
        for filename in filelist:
            #filename = str(name)
            filenumber = int(filename[4:9])
            if start_number == 0:
                start_number = filenumber
            f = get_by_filenumber(filenumber)
            if f is not None:
                Count_time = f['entry/collection_time'][0]
                Descrip = str(f['entry/sample/description'][0])     
                Descrip = Descrip[2:]
                Descrip = Descrip[:-1]
                if Count_time > 29 and str(Descrip).find("Align") == -1 and filenumber not in Excluded_Filenumbers and str(Descrip).find("align") == -1 and str(Descrip).find("Test") == -1 and str(Descrip).find("test") == -1:
                    FileNumberList.append(filenumber)
                    print('Reading:', filenumber, ' ', Descrip)
                    Listed_Config = str(f['entry/DAS_logs/configuration/key'][0])
                    Listed_Config = Listed_Config[2:]
                    Listed_Config = Listed_Config[:-1]
                    Sample_Name = Descrip.replace(Listed_Config, '')
                    Not_Sample = ['T_UU', 'T_DU', 'T_DD', 'T_UD', 'T_SM', 'T_NP', 'HeIN', 'HeOUT', 'S_UU', 'S_DU', 'S_DD', 'S_UD', 'S_NP', 'S_HeU', 'S_HeD', 'S_SMU', 'S_SMD']
                    for i in Not_Sample:
                        Sample_Name = Sample_Name.replace(i, '')
                    Desired_Temp = 'na'
                    if "temp" in f['entry/DAS_logs/']:
                        Desired_Temp = str(f['entry/DAS_logs/temp/desiredPrimaryNode'][(0)])
                        record_temp = 1    
                    Voltage = 'na'
                    if "adam4021" in f['entry/DAS_logs/']:
                        Voltage = str(f['entry/DAS_logs/adam4021/voltage'][(0)])
                        record_adam4021 = 1
                    DT5 = Desired_Temp + " K,"
                    DT4 = Desired_Temp + " K"
                    DT3 = Desired_Temp + "K,"
                    DT2 = Desired_Temp + "K"
                    DT1 = Desired_Temp
                    V5 = Voltage + " V,"
                    V4 = Voltage + " V"
                    V3 = Voltage + "V,"
                    V2 = Voltage + "V"
                    V1 = Voltage
                    Z = "/"
                    Not_Sample = [DT5, DT4, DT3, DT2, DT1, V5, V4, V3, V2, V1, Z]
                    for i in Not_Sample:
                        Sample_Name = Sample_Name.replace(i, '')
                    Sample_Name = Sample_Name.replace(' ', '')
                    Sample_Base = Sample_Name
                    Sample_Name = Sample_Name + '_' + str(Voltage) + 'V_' + str(Desired_Temp) + 'K'
                    Purpose = f['entry/reduction/file_purpose'][()] #SCATT, TRANS, HE3
                    Intent = f['entry/reduction/intent'][()] #Sample, Empty, Blocked Beam, Open Beam
                    if filenumber in ReAssignBlockBeam:
                        Intent = [b'Blocked Beam']
                    if filenumber in ReAssignEmpty:
                        Intent = [b'Empty']
                    if filenumber in ReAssignOpen:
                        Intent = [b'Open']
                    Type = str(f['entry/sample/description'][()])
                    if YesNoRenameEmpties > 0 and "Empty" in str(Intent):
                        Sample_Name = "Empty"
                    End_time = dateutil.parser.parse(f['entry/end_time'][0])
                    TimeOfMeasurement = (End_time.timestamp() - Count_time/2)/3600.0 #in hours
                    Trans_Counts = f['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    MonCounts = f['entry/control/monitor_counts'][0]
                    Trans_Distance = f['entry/instrument/detector_{ds}/distance'.format(ds=TransPanel)][0]
                    Desired_Attenuation = f['entry/DAS_logs/attenuator/attenuator'][0]
                    Attenuation = f['/entry/DAS_logs/counter/actualAttenuatorsDropped'][0]
                    Wavelength = f['entry/DAS_logs/wavelength/wavelength'][0]
                    Config = VSANS_Config_ID(filenumber)
                    if "frontPolarization" in f['entry/DAS_logs/']:
                        FrontPolDirection = f['entry/DAS_logs/frontPolarization/direction'][()]
                    else:
                        FrontPolDirection = [b'UNPOLARIZED']
                    if "backPolarization" in f['entry/DAS_logs/']:
                        BackPolDirection = f['entry/DAS_logs/backPolarization/direction'][()]
                    else:
                        BackPolDirection = [b'UNPOLARIZED']

                    GuideHolder = f['entry/DAS_logs/guide/guide'][0]
                    if str(GuideHolder).find("CONV") == -1:
                        if int(GuideHolder) == 0:
                            FrontPolDirection = [b'UNPOLARIZED']
                    '''Want to populate Config representative filenumbers on scattering filenumber'''
                    config_filenumber = 0
                    if str(Purpose).find("SCATT") != -1:
                        config_filenumber = filenumber
                    if Config not in Configs:
                        Configs[Config] = config_filenumber
                    if Configs[Config] == 0 and config_filenumber != 0:
                        Configs[Config] = config_filenumber
                    if Config not in BlockBeam:
                        BlockBeam[Config] = {'Scatt':{'File' : 'NA'}, 'Trans':{'File' : 'NA', 'CountsPerSecond' : 'NA'}, 'ExampleFile' : filenumber}
                    if str(Intent).find("Blocked") != -1:
                        if Config not in BlockBeam:
                             BlockBeam[Config] = {'Scatt':{'File' : 'NA'}, 'Trans':{'File' : 'NA', 'CountsPerSecond' : 'NA'},  'ExampleFile' : filenumber}
                        if str(Purpose).find("TRANS") != -1 or str(Purpose).find("HE3") != -1:
                            if 'NA' in BlockBeam[Config]['Trans']['File']:
                                BlockBeam[Config]['Trans']['File'] = [filenumber]
                                BlockBeam[Config]['Trans']['CountsPerSecond'] = [Trans_Counts/Count_time]
                            else:
                                BlockBeam[Config]['Trans']['File'].append(filenumber)
                                BlockBeam[Config]['Trans']['CountsPerSecond'].append(Trans_Counts/Count_time)
                        elif str(Purpose).find("SCATT") != -1:
                            if 'NA' in BlockBeam[Config]['Scatt']['File']:
                                BlockBeam[Config]['Scatt']['File'] = [filenumber]
                            else:
                                BlockBeam[Config]['Scatt']['File'].append(filenumber)
                    elif str(Intent).find("Sample") != -1 or str(Intent).find("Empty") != -1 or str(Intent).find("Open") != -1:
                        if len(Sample_Names) < 1:
                            Sample_Names = [Sample_Name]
                        else:
                            if Sample_Name not in Sample_Names:
                                Sample_Names.append(Sample_Name)
                        if len(Sample_Bases) < 1:
                            Sample_Bases = [Sample_Base]
                        else:
                            if Sample_Base not in Sample_Bases:
                                Sample_Bases.append(Sample_Base)
                        Intent_short = str(Intent)
                        Intent_short = Intent_short[3:-2]
                        Intent_short = Intent_short.replace(' Cell', '')
                        Intent_short = Intent_short.replace(' Beam', '')
                        if str(Purpose).find("SCATT") != -1:
                            if Sample_Name not in Scatt:
                                Scatt[Sample_Name] = {'Intent': Intent_short, 'Sample_Base': Sample_Base, 'Config(s)' : {Config : {'Unpol': 'NA', 'U' : 'NA', 'D' : 'NA','UU' : 'NA', 'DU' : 'NA', 'DD' : 'NA', 'UD' : 'NA', 'UU_Time' : 'NA', 'DU_Time' : 'NA', 'DD_Time' : 'NA', 'UD_Time' : 'NA'}}}
                            if Config not in Scatt[Sample_Name]['Config(s)']:
                                Scatt[Sample_Name]['Config(s)'][Config] = {'Unpol': 'NA', 'U' : 'NA', 'D' : 'NA','UU' : 'NA', 'DU' : 'NA', 'DD' : 'NA', 'UD' : 'NA', 'UU_Time' : 'NA', 'DU_Time' : 'NA', 'DD_Time' : 'NA', 'UD_Time' : 'NA'}
                            if str(FrontPolDirection).find("UNPOLARIZED") != -1 and str(BackPolDirection).find("UNPOLARIZED") != -1:
                                if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['Unpol']:
                                    Scatt[Sample_Name]['Config(s)'][Config]['Unpol'] = [filenumber]
                                else:
                                    Scatt[Sample_Name]['Config(s)'][Config]['Unpol'].append(filenumber)
                            if str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("UNPOLARIZED") != -1:
                                if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['U']:
                                    Scatt[Sample_Name]['Config(s)'][Config]['U'] = [filenumber]
                                else:
                                    Scatt[Sample_Name]['Config(s)'][Config]['U'].append(filenumber)
                            if str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("UNPOLARIZED") != -1:
                                if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['D']:
                                    Scatt[Sample_Name]['Config(s)'][Config]['D'] = [filenumber]
                                else:
                                    Scatt[Sample_Name]['Config(s)'][Config]['D'].append(filenumber)
                            if YesNoManualHe3Entry != 1:        
                                if str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("UP") != -1:
                                    if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['UU']:
                                        Scatt[Sample_Name]['Config(s)'][Config]['UU'] = [filenumber]
                                        Scatt[Sample_Name]['Config(s)'][Config]['UU_Time'] = [TimeOfMeasurement]
                                    else:
                                        Scatt[Sample_Name]['Config(s)'][Config]['UU'].append(filenumber)
                                        Scatt[Sample_Name]['Config(s)'][Config]['UU_Time'].append(TimeOfMeasurement)                                       
                                if str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("UP") != -1:
                                    if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['DU']:
                                        Scatt[Sample_Name]['Config(s)'][Config]['DU'] = [filenumber]
                                        Scatt[Sample_Name]['Config(s)'][Config]['DU_Time'] = [TimeOfMeasurement]
                                    else:
                                        Scatt[Sample_Name]['Config(s)'][Config]['DU'].append(filenumber)
                                        Scatt[Sample_Name]['Config(s)'][Config]['DU_Time'].append(TimeOfMeasurement)

                                if str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("DOWN") != -1:
                                    if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['DD']:
                                        Scatt[Sample_Name]['Config(s)'][Config]['DD'] = [filenumber]
                                        Scatt[Sample_Name]['Config(s)'][Config]['DD_Time'] = [TimeOfMeasurement]
                                    else:
                                        Scatt[Sample_Name]['Config(s)'][Config]['DD'].append(filenumber)
                                        Scatt[Sample_Name]['Config(s)'][Config]['DD_Time'].append(TimeOfMeasurement)
                                        
                                if str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("DOWN") != -1:
                                    if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['UD']:
                                        Scatt[Sample_Name]['Config(s)'][Config]['UD'] = [filenumber]
                                        Scatt[Sample_Name]['Config(s)'][Config]['UD_Time'] = [TimeOfMeasurement]
                                    else:
                                        Scatt[Sample_Name]['Config(s)'][Config]['UD'].append(filenumber)
                                        Scatt[Sample_Name]['Config(s)'][Config]['UD_Time'].append(TimeOfMeasurement)
                            else:
                                if Type[-6:-2] == 'S_UU': #str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("UP") != -1:
                                    if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['UU']:
                                        Scatt[Sample_Name]['Config(s)'][Config]['UU'] = [filenumber]
                                        Scatt[Sample_Name]['Config(s)'][Config]['UU_Time'] = [TimeOfMeasurement]
                                    else:
                                        Scatt[Sample_Name]['Config(s)'][Config]['UU'].append(filenumber)
                                        Scatt[Sample_Name]['Config(s)'][Config]['UU_Time'].append(TimeOfMeasurement)
                                        
                                if Type[-6:-2] == 'S_DU': #str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("UP") != -1:
                                    if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['DU']:
                                        Scatt[Sample_Name]['Config(s)'][Config]['DU'] = [filenumber]
                                        Scatt[Sample_Name]['Config(s)'][Config]['DU_Time'] = [TimeOfMeasurement]
                                    else:
                                        Scatt[Sample_Name]['Config(s)'][Config]['DU'].append(filenumber)
                                        Scatt[Sample_Name]['Config(s)'][Config]['DU_Time'].append(TimeOfMeasurement)

                                if Type[-6:-2] == 'S_DD': #str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("DOWN") != -1:
                                    if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['DD']:
                                        Scatt[Sample_Name]['Config(s)'][Config]['DD'] = [filenumber]
                                        Scatt[Sample_Name]['Config(s)'][Config]['DD_Time'] = [TimeOfMeasurement]
                                    else:
                                        Scatt[Sample_Name]['Config(s)'][Config]['DD'].append(filenumber)
                                        Scatt[Sample_Name]['Config(s)'][Config]['DD_Time'].append(TimeOfMeasurement)
                                        
                                if Type[-6:-2] == 'S_UD': #str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("DOWN") != -1:
                                    if 'NA' in Scatt[Sample_Name]['Config(s)'][Config]['UD']:
                                        Scatt[Sample_Name]['Config(s)'][Config]['UD'] = [filenumber]
                                        Scatt[Sample_Name]['Config(s)'][Config]['UD_Time'] = [TimeOfMeasurement]
                                    else:
                                        Scatt[Sample_Name]['Config(s)'][Config]['UD'].append(filenumber)
                                        Scatt[Sample_Name]['Config(s)'][Config]['UD_Time'].append(TimeOfMeasurement)     
                        if str(Purpose).find("TRANS") != -1:
                            if Sample_Name not in Trans:
                                Trans[Sample_Name] = {'Intent': Intent_short, 'Sample_Base': Sample_Base, 'Config(s)' : {Config : {'Unpol_Files': 'NA', 'U_Files' : 'NA', 'D_Files' : 'NA','Unpol_Trans_Cts': 'NA', 'U_Trans_Cts' : 'NA', 'D_Trans_Cts' : 'NA'}}}
                            if Config not in Trans[Sample_Name]['Config(s)']:
                                Trans[Sample_Name]['Config(s)'][Config] = {'Unpol_Files': 'NA', 'U_Files' : 'NA', 'D_Files': 'NA','Unpol_Trans_Cts': 'NA', 'U_Trans_Cts' : 'NA', 'D_Trans_Cts' : 'NA'}
                            if Sample_Name not in Pol_Trans:
                                Pol_Trans[Sample_Name] = {'T_UU' : {'File' : 'NA'},
                                                          'T_DU' : {'File' : 'NA'},
                                                          'T_DD' : {'File' : 'NA'},
                                                          'T_UD' : {'File' : 'NA'},
                                                          'T_SM' : {'File' : 'NA'},
                                                          'Config' : 'NA'
                                                          }
                            if str(FrontPolDirection).find("UNPOLARIZED") != -1 and str(BackPolDirection).find("UNPOLARIZED") != -1:
                                if 'NA' in Trans[Sample_Name]['Config(s)'][Config]['Unpol_Files']:
                                    Trans[Sample_Name]['Config(s)'][Config]['Unpol_Files'] = [filenumber]
                                else:
                                    Trans[Sample_Name]['Config(s)'][Config]['Unpol_Files'].append(filenumber)
                            if str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("UNPOLARIZED") != -1:
                                if 'NA' in Trans[Sample_Name]['Config(s)'][Config]['U_Files']:
                                    Trans[Sample_Name]['Config(s)'][Config]['U_Files'] = [filenumber]
                                else:
                                    Trans[Sample_Name]['Config(s)'][Config]['U_Files'].append(filenumber)
                            if str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("UNPOLARIZED") != -1:
                                if 'NA' in Trans[Sample_Name]['Config(s)'][Config]['D_Files']:
                                    Trans[Sample_Name]['Config(s)'][Config]['D_Files'] = [filenumber]
                                else:
                                    Trans[Sample_Name]['Config(s)'][Config]['D_Files'].append(filenumber)
                            if YesNoManualHe3Entry != 1:
                                if str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("UP") != -1:
                                    UU_filenumber = filenumber
                                    UU_Time = (End_time.timestamp() - Count_time/2)/3600.0
                                if str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("UP") != -1:
                                    DU_filenumber = filenumber
                                    DU_Time = (End_time.timestamp() - Count_time/2)/3600.0
                                if str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("DOWN") != -1:
                                    DD_filenumber = filenumber
                                    DD_Time = (End_time.timestamp() - Count_time/2)/3600.0
                                if str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("DOWN") != -1:
                                    UD_filenumber = filenumber
                                    UD_Time = (End_time.timestamp() - Count_time/2)/3600.0
                                if str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("UNPOLARIZED") != -1:
                                    SM_filenumber = filenumber
                                    if SM_filenumber - UU_filenumber == 4:
                                        if 'NA' in Pol_Trans[Sample_Name]['T_UU']['File']:
                                            Pol_Trans[Sample_Name]['T_UU']['File'] = [UU_filenumber]
                                            Pol_Trans[Sample_Name]['T_UU']['Meas_Time'] = [UU_Time]
                                        else:
                                            Pol_Trans[Sample_Name]['T_UU']['File'].append(UU_filenumber)
                                            Pol_Trans[Sample_Name]['T_UU']['Meas_Time'].append(UU_Time)
                                        if 'NA' in Pol_Trans[Sample_Name]['T_DU']['File']:
                                            Pol_Trans[Sample_Name]['T_DU']['File'] = [DU_filenumber]
                                            Pol_Trans[Sample_Name]['T_DU']['Meas_Time'] = [DU_Time]
                                        else:
                                            Pol_Trans[Sample_Name]['T_DU']['File'].append(DU_filenumber)
                                            Pol_Trans[Sample_Name]['T_DU']['Meas_Time'].append(DU_Time)
                                        if 'NA' in Pol_Trans[Sample_Name]['T_DD']['File']:
                                            Pol_Trans[Sample_Name]['T_DD']['File'] = [DD_filenumber]
                                            Pol_Trans[Sample_Name]['T_DD']['Meas_Time'] = [DD_Time]
                                        else:
                                            Pol_Trans[Sample_Name]['T_DD']['File'].append(DD_filenumber)
                                            Pol_Trans[Sample_Name]['T_DD']['Meas_Time'].append(DD_Time)
                                        if 'NA' in Pol_Trans[Sample_Name]['T_UD']['File']:
                                            Pol_Trans[Sample_Name]['T_UD']['File'] = [UD_filenumber]
                                            Pol_Trans[Sample_Name]['T_UD']['Meas_Time'] = [UD_Time]
                                        else:
                                            Pol_Trans[Sample_Name]['T_UD']['File'].append(UD_filenumber)
                                            Pol_Trans[Sample_Name]['T_UD']['Meas_Time'].append(UD_Time)
                                        if 'NA' in Pol_Trans[Sample_Name]['T_SM']['File']:
                                            Pol_Trans[Sample_Name]['T_SM']['File'] = [SM_filenumber]
                                        else:
                                            Pol_Trans[Sample_Name]['T_SM']['File'].append(SM_filenumber)
                                        if 'NA' in Pol_Trans[Sample_Name]['Config']:
                                            Pol_Trans[Sample_Name]['Config'] = [Config]
                                        else:
                                            Pol_Trans[Sample_Name]['Config'].append(Config)
                            else:
                                if Type[-6:-2] == 'T_UU': #str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("UP") != -1:
                                    UU_filenumber = filenumber
                                    UU_Time = (End_time.timestamp() - Count_time/2)/3600.0
                                if Type[-6:-2] == 'T_DU': #str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("UP") != -1:
                                    DU_filenumber = filenumber
                                    DU_Time = (End_time.timestamp() - Count_time/2)/3600.0
                                if Type[-6:-2] == 'T_DD': #str(FrontPolDirection).find("DOWN") != -1 and str(BackPolDirection).find("DOWN") != -1:
                                    DD_filenumber = filenumber
                                    DD_Time = (End_time.timestamp() - Count_time/2)/3600.0
                                if Type[-6:-2] == 'T_UD': #str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("DOWN") != -1:
                                    UD_filenumber = filenumber
                                    UD_Time = (End_time.timestamp() - Count_time/2)/3600.0
                                if Type[-6:-2] == 'T_SM': #str(FrontPolDirection).find("UP") != -1 and str(BackPolDirection).find("UNPOLARIZED") != -1:
                                    SM_filenumber = filenumber
                                    if SM_filenumber - UU_filenumber == 4:
                                        if 'NA' in Pol_Trans[Sample_Name]['T_UU']['File']:
                                            Pol_Trans[Sample_Name]['T_UU']['File'] = [UU_filenumber]
                                            Pol_Trans[Sample_Name]['T_UU']['Meas_Time'] = [UU_Time]
                                        else:
                                            Pol_Trans[Sample_Name]['T_UU']['File'].append(UU_filenumber)
                                            Pol_Trans[Sample_Name]['T_UU']['Meas_Time'].append(UU_Time)
                                        if 'NA' in Pol_Trans[Sample_Name]['T_DU']['File']:
                                            Pol_Trans[Sample_Name]['T_DU']['File'] = [DU_filenumber]
                                            Pol_Trans[Sample_Name]['T_DU']['Meas_Time'] = [DU_Time]
                                        else:
                                            Pol_Trans[Sample_Name]['T_DU']['File'].append(DU_filenumber)
                                            Pol_Trans[Sample_Name]['T_DU']['Meas_Time'].append(DU_Time)
                                        if 'NA' in Pol_Trans[Sample_Name]['T_DD']['File']:
                                            Pol_Trans[Sample_Name]['T_DD']['File'] = [DD_filenumber]
                                            Pol_Trans[Sample_Name]['T_DD']['Meas_Time'] = [DD_Time]
                                        else:
                                            Pol_Trans[Sample_Name]['T_DD']['File'].append(DD_filenumber)
                                            Pol_Trans[Sample_Name]['T_DD']['Meas_Time'].append(DD_Time)
                                        if 'NA' in Pol_Trans[Sample_Name]['T_UD']['File']:
                                            Pol_Trans[Sample_Name]['T_UD']['File'] = [UD_filenumber]
                                            Pol_Trans[Sample_Name]['T_UD']['Meas_Time'] = [UD_Time]
                                        else:
                                            Pol_Trans[Sample_Name]['T_UD']['File'].append(UD_filenumber)
                                            Pol_Trans[Sample_Name]['T_UD']['Meas_Time'].append(UD_Time)
                                        if 'NA' in Pol_Trans[Sample_Name]['T_SM']['File']:
                                            Pol_Trans[Sample_Name]['T_SM']['File'] = [SM_filenumber]
                                        else:
                                            Pol_Trans[Sample_Name]['T_SM']['File'].append(SM_filenumber)
                                        if 'NA' in Pol_Trans[Sample_Name]['Config']:
                                            Pol_Trans[Sample_Name]['Config'] = [Config]
                                        else:
                                            Pol_Trans[Sample_Name]['Config'].append(Config)
                        if str(Purpose).find("HE3") != -1:
                            HE3Type = str(f['entry/sample/description'][()])
                            if HE3Type[-7:-2] == 'HeOUT':
                                if Sample_Name not in Trans:
                                    Trans[Sample_Name] = {'Intent': Intent_short, 'Sample_Base': Sample_Base, 'Config(s)' : {Config : {'Unpol_Files': 'NA', 'U_Files' : 'NA', 'D_Files' : 'NA','Unpol_Trans_Cts': 'NA', 'U_Trans_Cts' : 'NA', 'D_Trans_Cts' : 'NA'}}}
                                if Config not in Trans[Sample_Name]['Config(s)']:
                                    Trans[Sample_Name]['Config(s)'][Config] = {'Unpol_Files': 'NA', 'U_Files' : 'NA', 'D_Files': 'NA','Unpol_Trans_Cts': 'NA', 'U_Trans_Cts' : 'NA', 'D_Trans_Cts' : 'NA'}
                                if 'NA' in Trans[Sample_Name]['Config(s)'][Config]['Unpol_Files']:
                                    Trans[Sample_Name]['Config(s)'][Config]['Unpol_Files'] = [filenumber]
                                else:
                                    Trans[Sample_Name]['Config(s)'][Config]['Unpol_Files'].append(filenumber)
                            if YesNoManualHe3Entry == 1:
                                if filenumber in New_HE3_Files:
                                    ScaledOpacity = MuValues[CellIdentifier]
                                    TE = TeValues[CellIdentifier]
                                    CellTimeIdentifier = (End_time.timestamp() - Count_time)/3600.0
                                    HE3Insert_Time = (End_time.timestamp() - Count_time)/3600.0
                                    CellIdentifier += 1    
                            else:
                                CellTimeIdentifier = f['/entry/DAS_logs/backPolarization/timestamp'][0]/3600000 #milliseconds to hours
                                CellName = str(f['entry/DAS_logs/backPolarization/name'][0])
                                CellName = CellName[2:]
                                CellName = CellName[:-1]
                                CellName = CellName + str(CellTimeIdentifier)
                                CellTimeIdentifier = f['/entry/DAS_logs/backPolarization/timestamp'][0]/3600000 #milliseconds to hours
                                if CellTimeIdentifier not in HE3_Trans:
                                    HE3Insert_Time = f['/entry/DAS_logs/backPolarization/timestamp'][0]/3600000 #milliseconds to hours
                                    Opacity = f['/entry/DAS_logs/backPolarization/opacityAt1Ang'][0]
                                    Wavelength = f['/entry/DAS_logs/wavelength/wavelength'][0]
                                    ScaledOpacity = Opacity*Wavelength
                                    TE = f['/entry/DAS_logs/backPolarization/glassTransmission'][0]
                            if HE3Type[-7:-2] == 'HeOUT':
                                HE3OUT_filenumber = filenumber
                                HE3OUT_config = Config
                                HE3OUT_sample = Sample_Name
                                HE3OUT_attenuators = int(f['entry/instrument/attenuator/num_atten_dropped'][0])
                            elif HE3Type[-7:-2] == ' HeIN':
                                HE3IN_filenumber = filenumber
                                HE3IN_config = Config
                                HE3IN_sample = Sample_Name
                                HE3IN_attenuators = int(f['entry/instrument/attenuator/num_atten_dropped'][0])
                                HE3IN_StartTime = (End_time.timestamp() - Count_time/2)/3600.0
                                if HE3OUT_filenumber > 0:
                                    if HE3OUT_config == HE3IN_config and HE3OUT_attenuators == HE3IN_attenuators and HE3OUT_sample == HE3IN_sample: #This implies that you must have a 3He out before 3He in of same config and atten
                                        if HE3Insert_Time not in HE3_Trans:
                                            HE3_Trans[CellTimeIdentifier] = {'Te' : TE,
                                                                         'Mu' : ScaledOpacity,
                                                                         'Insert_time' : HE3Insert_Time}
                                        Elasped_time = HE3IN_StartTime - HE3Insert_Time
                                        if "Elasped_time" not in HE3_Trans[CellTimeIdentifier]:
                                            HE3_Trans[CellTimeIdentifier]['Config'] = [HE3IN_config]
                                            HE3_Trans[CellTimeIdentifier]['HE3_OUT_file'] = [HE3OUT_filenumber]
                                            HE3_Trans[CellTimeIdentifier]['HE3_IN_file'] = [HE3IN_filenumber]
                                            HE3_Trans[CellTimeIdentifier]['Elasped_time'] = [Elasped_time]
                                            HE3_Trans[CellTimeIdentifier]['Cell_name'] = [CellName]
                                        else:
                                            HE3_Trans[CellTimeIdentifier]['Config'].append(HE3IN_config)
                                            HE3_Trans[CellTimeIdentifier]['HE3_OUT_file'].append(HE3OUT_filenumber)
                                            HE3_Trans[CellTimeIdentifier]['HE3_IN_file'].append(HE3IN_filenumber)
                                            HE3_Trans[CellTimeIdentifier]['Elasped_time'].append(Elasped_time)
                                            HE3_Trans[CellTimeIdentifier]['Cell_name'].append(CellName)
    return Sample_Names, Sample_Bases, Configs, BlockBeam, Scatt, Trans, Pol_Trans, HE3_Trans, start_number, FileNumberList

def VSANS_AttenuatorTable(wavelength, attenuation):

    if attenuation <= 0:
        attn_index = 0
    elif attenuation >= 15:
        attn_index = 15
    else:
        attn_index = int(attenuation)
    if wavelength < 4.52:
        wavelength = 4.52
    if wavelength > 19.0 and wavelength != 5300 and wavelength != 6200000:
        wavelength = 19.0        
    Attn_Table = {}
    Attn_Table[4.52] = [1,0.446,0.20605,0.094166,0.042092,0.019362,0.0092358,0.0042485,0.002069,0.00096002,0.00045601,0.00021113,9.67E-05,4.55E-05,2.25E-05,1.11E-05]
    Attn_Table[5.01] = [1,0.431,0.19352,0.085922,0.03729,0.016631,0.0076671,0.0034272,0.0016896,0.00075357,0.00034739,0.00015667,6.97E-05,3.25E-05,1.57E-05,8.00E-06]
    Attn_Table[5.5] = [1,0.418,0.18225,0.078184,0.032759,0.014152,0.0063401,0.0027516,0.0013208,0.00057321,0.00025623,0.00011171,4.92E-05,2.27E-05,1.09E-05,5.77E-06]
    Attn_Table[5.99] = [1,0.406,0.17255,0.071953,0.029501,0.01239,0.0054146,0.0022741,0.0010643,0.0004502,0.00019584,8.38E-05,3.61E-05,1.70E-05,8.35E-06,4.65E-06]
    Attn_Table[6.96] = [1,0.382,0.15471,0.06111,0.023894,0.0094621,0.0039362,0.0015706,0.00069733,0.00027963,0.0001166,4.86E-05,2.12E-05,1.06E-05,5.54E-06,3.65E-06]
    Attn_Table[7.94] = [1,0.364,0.14014,0.052552,0.019077,0.0071919,0.0028336,0.0010796,0.00045883,0.00017711,7.14E-05,2.90E-05,1.37E-05,7.78E-06,4.54E-06,3.56E-06]
    Attn_Table[9] = [1,0.34199,0.12617,0.045063,0.015551,0.0055606,0.0020986,0.00075427,0.00031101,0.00011673,0.000045324,1.91E-05,8.51E-06,4.82E-06,2.85E-06,2.14E-06]
    Attn_Table[11] = [1,0.31805,0.10886,0.035741,0.011411,0.0037545,0.0013263,0.00043766,0.00016884,5.99E-05,2.23E-05,9.44E-06,5.57E-06,4.10E-06,2.79E-06,2.46E-06]
    Attn_Table[13] = [1,0.298,0.096286,0.029689,0.0088395,0.0027373,0.00090878,0.00028892,0.00011004,3.88E-05,1.44E-05,6.91E-06,5.28E-06,4.17E-06,2.91E-06,2.76E-06]
    Attn_Table[15] = [1,0.27964,0.085614,0.024762,0.0069407,0.0020229,0.00064044,0.00019568,7.44E-05,2.79E-05,1.10E-05,6.34E-06,5.47E-06,4.89E-06,3.66E-06,3.45E-06]
    Attn_Table[17] = [1,0.26364,0.075577,0.020525,0.0053394,0.0014753,0.00044466,0.00013278,5.40E-05,2.31E-05,1.04E-05,7.36E-06,7.33E-06,6.69E-06,5.20E-06,4.75E-06]
    Attn_Table[19] = [1,0.24614,0.065873,0.016961,0.0040631,0.0010583,0.00031229,9.87E-05,4.85E-05,2.77E-05,1.68E-05,1.47E-05,1.52E-05,1.44E-05,1.26E-05,1.19E-05]
    Attn_Table[5300] = [1,0.429,0.19219,0.085141,0.037122,0.016668,0.0078004,0.0035414,0.0017742,0.0008126,0.00038273,0.00017682,8.12E-05,3.89E-05,1.95E-05,1.00E-05]
    Attn_Table[6200000] = [1,0.4152,0.18249,0.079458,0.034065,0.014849,0.0067964,0.003016,0.001485,0.00066483,0.00030864,0.00014094,6.38E-05,3.02E-05,1.50E-05,7.73E-06]
    if wavelength == 5300:
        Trans = Attn_Table[5300][attn_index]
    elif wavelength == 6200000:
        Trans = Attn_Table[6200000][attn_index]
    else:
        Wavelength_Min = 4.52
        Wavelength_Max = 4.52
        Max_trip = 0
        for i in Attn_Table:
            if wavelength >= i:
                Wavelength_Min = i
            if wavelength <= i and Max_trip == 0:
                Wavelength_Max = i
                Max_trip = 1  
        Trans_MinWave = Attn_Table[Wavelength_Min][attn_index]
        Trans_MaxWave = Attn_Table[Wavelength_Max][attn_index]
        if Wavelength_Max > Wavelength_Min:
            Trans = Trans_MinWave + (wavelength - Wavelength_Min)*(Trans_MaxWave - Trans_MinWave)/(Wavelength_Max - Wavelength_Min)
        else:
            Trans = Trans_MinWave  
    return Trans

def VSANS_MakeTransMask(filenumber, Config, DetectorPanel):

    mask_it = {}
    relevant_detectors = short_detectors
    CvBYesNo = 0
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors
        CvBYesNo = 1
    f = get_by_filenumber(filenumber)
    for dshort in relevant_detectors:
        data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
        mask_it[dshort] = np.zeros_like(data)
        x_pixel_size = f['entry/instrument/detector_{ds}/x_pixel_size'.format(ds=dshort)][0]/10.0
        y_pixel_size = f['entry/instrument/detector_{ds}/y_pixel_size'.format(ds=dshort)][0]/10.0
        beam_center_x = f['entry/instrument/detector_{ds}/beam_center_x'.format(ds=dshort)][0]
        beam_center_y = f['entry/instrument/detector_{ds}/beam_center_y'.format(ds=dshort)][0]
        dimX = f['entry/instrument/detector_{ds}/pixel_num_x'.format(ds=dshort)][0]
        dimY = f['entry/instrument/detector_{ds}/pixel_num_y'.format(ds=dshort)][0]
        if CvBYesNo == 0:
            beamstop_diameter = f['/entry/DAS_logs/C2BeamStop/diameter'][0]/10.0 #beam stop in cm; sits right in front of middle detector?
        else:
            beamstop_diameter = 10.0
        if dshort == 'MT' or dshort == 'MB' or dshort == 'FT' or dshort == 'FB':
            setback = f['entry/instrument/detector_{ds}/setback'.format(ds=dshort)][0]
            vertical_offset = f['entry/instrument/detector_{ds}/vertical_offset'.format(ds=dshort)][0]
            lateral_offset = 0
        else:
            setback = 0
            vertical_offset = 0
            lateral_offset = f['entry/instrument/detector_{ds}/lateral_offset'.format(ds=dshort)][0]
        
        if dshort != 'B':
            coeffs = f['entry/instrument/detector_{ds}/spatial_calibration'.format(ds=dshort)][0][0]/10.0
            panel_gap = f['entry/instrument/detector_{ds}/panel_gap'.format(ds=dshort)][0]/10.0
        if dshort == 'B':
            realDistX =  x_pixel_size*(0.5)
            realDistY =  y_pixel_size*(0.5)
        else:
            position_key = dshort[1]
            if position_key == 'T':
                realDistX =  coeffs
                realDistY =  0.5 * y_pixel_size + vertical_offset + panel_gap/2.0
            elif position_key == 'B':
                realDistX =  coeffs
                realDistY =  vertical_offset - (dimY - 0.5)*y_pixel_size - panel_gap/2.0
            elif position_key == 'L':
                realDistX =  lateral_offset - (dimX - 0.5)*x_pixel_size - panel_gap/2.0
                realDistY =  coeffs
            elif position_key == 'R':
                realDistX =  x_pixel_size*(0.5) + lateral_offset + panel_gap/2.0
                realDistY =  coeffs
        X, Y = np.indices(data.shape)
        if dshort == 'B':
            x0_pos =  realDistX - beam_center_x*x_pixel_size + (X)*x_pixel_size 
            y0_pos =  realDistY - beam_center_y*y_pixel_size + (Y)*y_pixel_size
        else:
            x0_pos =  realDistX - beam_center_x + (X)*x_pixel_size 
            y0_pos =  realDistY - beam_center_y + (Y)*y_pixel_size
        R = np.sqrt(np.power(x0_pos, 2) + np.power(y0_pos, 2))
        if dshort == DetectorPanel and CvBYesNo == 0:
            mask_it[dshort][R <= 1.2*beamstop_diameter/2.0] = 1.0
        if dshort == DetectorPanel and CvBYesNo == 1:
            mask_it[dshort][R <= 2.0*beamstop_diameter/2.0] = 1.0
    return mask_it

def VSANS_ShareSampleBaseTransCatalog(Trans, Scatt):
    for Sample in Scatt:
        for Config in Scatt[Sample]['Config(s)']:
            if Sample not in Trans:
                Intent2 = Scatt[Sample]['Intent']
                Base2 = Scatt[Sample]['Sample_Base']
                Trans[Sample] = {'Intent': Intent2, 'Sample_Base': Base2, 'Config(s)' : {Config : {'Unpol_Files': 'NA', 'U_Files' : 'NA', 'D_Files' : 'NA','Unpol_Trans_Cts': 'NA', 'U_Trans_Cts' : 'NA', 'D_Trans_Cts' : 'NA'}}}
            else:
                if Config not in Trans[Sample]['Config(s)']:
                    Trans[Sample]['Config(s)'][Config] = {'Unpol_Files': 'NA', 'U_Files' : 'NA', 'D_Files': 'NA','Unpol_Trans_Cts': 'NA', 'U_Trans_Cts' : 'NA', 'D_Trans_Cts' : 'NA'}
    UnpolBases = {}
    UnpolAssociatedTrans = {}
    UpBases = {}
    UpAssociatedTrans = {}
    for Sample in Trans:
        Base = Trans[Sample]['Sample_Base']
        if 'Config(s)' in Trans[Sample]:
            for Config in Trans[Sample]['Config(s)']:
                if 'NA' not in Trans[Sample]['Config(s)'][Config]['Unpol_Files']:
                    fn = Trans[Sample]['Config(s)'][Config]['Unpol_Files'][0]
                    if Config not in UnpolBases:
                        UnpolBases[Config] = [Base]
                        UnpolAssociatedTrans[Config] = [fn]
                    elif Base not in UnpolBases[Config]:
                        UnpolBases[Config].append(Base)
                        UnpolAssociatedTrans[Config].append(fn)
                if 'NA' not in Trans[Sample]['Config(s)'][Config]['U_Files']:
                    fn = Trans[Sample]['Config(s)'][Config]['U_Files'][0]
                    if Config not in UpBases:
                        UpBases[Config] = [Base]
                        UpAssociatedTrans[Config] = [fn]
                    elif Base not in UpBases[Config]:
                        UpBases[Config].append(Base)
                        UpAssociatedTrans[Config].append(fn)
    for Sample in Trans:
        Base = Trans[Sample]['Sample_Base']
        if 'Config(s)' in Trans[Sample]:
            for Config in Trans[Sample]['Config(s)']:
                if 'NA' in Trans[Sample]['Config(s)'][Config]['Unpol_Files']:
                    if Config in UnpolBases:
                        if Base in UnpolBases[Config]:
                            for i in [i for i,x in enumerate(UnpolBases[Config]) if x == Base]:
                                Trans[Sample]['Config(s)'][Config]['Unpol_Files'] = [UnpolAssociatedTrans[Config][i]]
                if 'NA' in Trans[Sample]['Config(s)'][Config]['U_Files']:
                    if Config in UpBases:
                        if Base in UpBases[Config]:
                            for i in [i for i,x in enumerate(UpBases[Config]) if x == Base]:
                                Trans[Sample]['Config(s)'][Config]['U_Files'] = [UpAssociatedTrans[Config][i]]
    return

def ReadIn_IGORMasks(filenumberlisting):
    Masks = {}
    single_mask = {}
    Mask_Record = {}
    filename = '0'
    Mask_files = [fn for fn in os.listdir("./") if fn.endswith("MASK.h5")]
    if len(Mask_files) >= 1:
        for name in Mask_files:
            filename = str(name)
            associated_filenumber = filename[:5]
            if associated_filenumber.isdigit() == True:
                if associated_filenumber not in str(filenumberlisting):
                    print('Need scan for filenumber ', associated_filenumber, ' to proces its associated mask.')
                else:    
                    ConfigID = VSANS_Config_ID(associated_filenumber)
                    
                    relevant_detectors = short_detectors
                    if str(ConfigID).find('CvB') != -1:
                        relevant_detectors = all_detectors
                    if ConfigID not in Masks:
                        Masks[ConfigID] = {'Trans' : 'NA', 'Scatt_Standard' : 'NA', 'Scatt_WithSolenoid' : 'NA'}
                        Mask_Record[ConfigID] = {'Trans' : 'NA', 'Scatt_Standard' : 'NA', 'Scatt_WithSolenoid' : 'NA'}
                    Type, SolenoidPosition = VSANS_File_Type(associated_filenumber)
                    f = get_by_filenumber(filenumber)
                    if f is not None:
                        for dshort in relevant_detectors:
                            mask_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            if ConvertHighResToSubset > 0 and dshort == 'B':
                                mask_holder = mask_data[HighResMinX:HighResMaxX+1,HighResMinY:HighResMaxY+1]
                                mask_data = mask_holder
                            '''
                            This reverses zeros and ones (assuming IGOR-made masks) so that zeros become the pixels to ignore:
                            '''
                            single_mask[dshort] = np.zeros_like(mask_data)
                            single_mask[dshort][mask_data == 0] = 1.0
                        if str(Type).find("TRANS") != -1:
                            Masks[ConfigID]['Trans'] = single_mask.copy()
                            Mask_Record[ConfigID]['Trans'] = name
                            print('Saved', filename, ' as Trans Mask for', ConfigID)  
                        if str(Type).find("SCATT") != -1 and str(SolenoidPosition).find("OUT") != -1:
                            Masks[ConfigID]['Scatt_Standard'] = single_mask.copy()
                            Mask_Record[ConfigID]['Scatt_Standard'] = name
                            print('Saved', filename, ' as Standard Scatt Mask for', ConfigID)                            
                        if str(Type).find("SCATT") != -1 and str(SolenoidPosition).find("IN") != -1:
                            Masks[ConfigID]['Scatt_WithSolenoid'] = single_mask.copy()
                            Mask_Record[ConfigID]['Scatt_WithSolenoid'] = name
                            print('Saved', filename, ' as Scatt Mask With Solenoid for', ConfigID)                     
    return Masks, Mask_Record

def VSANS_BlockedBeamCountsPerSecond_ListOfFiles(filelist, Config, examplefilenumber):

    BB_Counts = {}
    BB_Unc = {}
    BB_Seconds = {}
    BB_CountsPerSecond = {}
    
    relevant_detectors = short_detectors
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors

    item_counter = 0
    for item in filelist:
        filename = input_path + "sans" + str(item) + ".nxs.ngv"
        f = get_by_filenumber(item)
        if f is not None:            
            Count_time = f['entry/collection_time'][0]
            if Count_time > 0:
                for dshort in relevant_detectors:
                    bb_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                    unc = np.sqrt(np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)]))
                
                    if item_counter < 1:
                        BB_Counts[dshort] = bb_data
                        BB_Seconds[dshort] = Count_time
                    else:
                        BB_Counts[dshort] = BB_Counts[dshort] + bb_data
                        BB_Seconds[dshort] = BB_Seconds[dshort] + Count_time
                    BB_CountsPerSecond[dshort] = BB_Counts[dshort]/BB_Seconds[dshort]
                    BB_Unc[dshort] = np.sqrt(BB_Counts[dshort])/BB_Seconds[dshort]
                item_counter += 1

    if len(BB_CountsPerSecond) < 1:
        f = get_by_filenumber(examplefilenumber)
        if f is not None:
            for dshort in relevant_detectors:
                data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                BB_CountsPerSecond[dshort] = np.zeros_like(data)
                BB_Unc[dshort] = np.zeros_like(data)

    return BB_CountsPerSecond, BB_Unc #returns empty list or 2D, detector-panel arrays

def VSANS_CalcABSTrans_BlockBeamList(trans_filenumber, BBList, DetectorPanel):
    #Uses VSANS_Config_ID(trans_filenumber) and
    #VSANS_MakeTransMask(filenumber, Config, DetectorPanel) and
    #VSANS_BlockedBeamCountsPerSecond_ListOfFiles(filelist, Config) and 
    #VSANS_AttenuatorTable(wavelength, attenuation)

    Config = VSANS_Config_ID(trans_filenumber)

    relevant_detectors = short_detectors
    CvBYesNo = 0
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors
        CvBYesNo = 1
    
    Mask = VSANS_MakeTransMask(trans_filenumber,Config, DetectorPanel)
    if Config in BBList:
        examplefilenumber = BBList[Config]['ExampleFile']
    else:
        examplefilenumber = 0
    BB, BB_Unc = VSANS_BlockedBeamCountsPerSecond_ListOfFiles(BBList, Config, examplefilenumber)
    f = get_by_filenumber(trans_filenumber)
    if f is not None:
        monitor_counts = f['entry/control/monitor_counts'][0]
        count_time = f['entry/collection_time'][0]
        wavelength = f['entry/DAS_logs/wavelength/wavelength'][0]
        desired_attenuation = f['entry/DAS_logs/attenuator/attenuator'][0]
        attenuation = f['/entry/DAS_logs/counter/actualAttenuatorsDropped'][0]
        attn_trans = VSANS_AttenuatorTable(wavelength, attenuation)
        abs_trans = 0
        abs_trans_unc = 0
        for dshort in relevant_detectors:
            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])    
            if dshort in BB and dshort in BB_Unc:
                trans = (data - BB[dshort]*count_time)*Mask[dshort]
                unc = np.sqrt(data + BB_Unc[dshort])*Mask[dshort]
            else:
                trans = (data)*Mask[dshort]
                unc = np.sqrt(data)*Mask[dshort]           
            abs_trans += (np.sum(trans)*1E8/monitor_counts)/attn_trans
            abs_trans_unc += (np.sqrt(np.sum(np.power(unc,2)))*1E8/monitor_counts)/attn_trans

        
    return abs_trans, abs_trans_unc

def VSANS_ProcessHe3TransCatalog(HE3_Trans, BlockBeam, DetectorPanel):
    #Uses VSANS_CalcABSTrans_BlockBeamList(trans_filenumber, BlockBeam, DetectorPanel) which uses
    #VSANS_MakeTransMask(filenumber, Config, DetectorPanel) and
    #VSANS_BlockedBeamCountsPerSecond_ListOfFiles(filelist, Config) and 
    #VSANS_AttenuatorTable(wavelength, attenuation)
    
    for Cell in HE3_Trans:
        if 'Elasped_time' in HE3_Trans[Cell]:
            counter = 0
            for InFile in HE3_Trans[Cell]['HE3_IN_file']:
                OutFile = HE3_Trans[Cell]['HE3_OUT_file'][counter]
                Config = HE3_Trans[Cell]['Config'][counter]
                BBList = [0]
                if Config in BlockBeam:
                    if 'NA' not in BlockBeam[Config]['Trans']['File']:
                        BBList = BlockBeam[Config]['Trans']['File']
                    elif 'NA' not in BlockBeam[Config]['Scatt']['File']:
                        BBList = BlockBeam[Config]['Scatt']['File']
                IN_trans, IN_trans_unc = VSANS_CalcABSTrans_BlockBeamList(InFile, BBList, DetectorPanel)
                OUT_trans, OUT_trans_unc = VSANS_CalcABSTrans_BlockBeamList(OutFile, BBList, DetectorPanel)
                trans = IN_trans / OUT_trans
                if 'Transmission' not in HE3_Trans[Cell]:
                    HE3_Trans[Cell]['Transmission'] = [trans]
                else:
                    HE3_Trans[Cell]['Transmission'].append(trans)                
                counter += 1 
    return

def VSANS_ProcessPolTransCatalog(Pol_Trans, BlockBeam, DetectorPanel):
    #Uses VSANS_CalcABSTrans_BlockBeamList(trans_filenumber, BlockBeam, DetectorPanel) which uses
    #VSANS_MakeTransMask(filenumber, Config, DetectorPanel) and
    #VSANS_BlockedBeamCountsPerSecond_ListOfFiles(filelist, Config) and 
    #VSANS_AttenuatorTable(wavelength, attenuation)
    for Samp in Pol_Trans:
        if 'NA' not in Pol_Trans[Samp]['T_UU']['File']:
            counter = 0
            for UUFile in Pol_Trans[Samp]['T_UU']['File']:
                DUFile = Pol_Trans[Samp]['T_DU']['File'][counter]
                DDFile = Pol_Trans[Samp]['T_DD']['File'][counter]
                UDFile = Pol_Trans[Samp]['T_UD']['File'][counter]
                SMFile = Pol_Trans[Samp]['T_SM']['File'][counter]
                Config = Pol_Trans[Samp]['Config'][counter]
                BBList = [0]
                if Config in BlockBeam:
                    if 'NA' not in BlockBeam[Config]['Trans']['File']:
                        BBList = BlockBeam[Config]['Trans']['File']
                    elif 'NA' not in BlockBeam[Config]['Scatt']['File']:
                        BBList = BlockBeam[Config]['Scatt']['File']
                UU_trans, UU_trans_unc = VSANS_CalcABSTrans_BlockBeamList(UUFile, BBList, DetectorPanel) #Masking done within this step
                DU_trans, DU_trans_unc = VSANS_CalcABSTrans_BlockBeamList(DUFile, BBList, DetectorPanel) #Masking done within this step
                DD_trans, DD_trans_unc = VSANS_CalcABSTrans_BlockBeamList(DDFile, BBList, DetectorPanel) #Masking done within this step
                UD_trans, UD_trans_unc = VSANS_CalcABSTrans_BlockBeamList(UDFile, BBList, DetectorPanel) #Masking done within this step
                SM_trans, SM_trans_unc = VSANS_CalcABSTrans_BlockBeamList(SMFile, BBList, DetectorPanel) #Masking done within this step
                if 'Trans' not in Pol_Trans[Samp]['T_UU']:
                    Pol_Trans[Samp]['T_UU']['Trans'] = [UU_trans/SM_trans]
                    Pol_Trans[Samp]['T_DU']['Trans'] = [DU_trans/SM_trans]
                    Pol_Trans[Samp]['T_DD']['Trans'] = [DD_trans/SM_trans]
                    Pol_Trans[Samp]['T_UD']['Trans'] = [UD_trans/SM_trans]
                    Pol_Trans[Samp]['T_SM']['Trans_Cts'] = [SM_trans]
                else:
                    Pol_Trans[Samp]['T_UU']['Trans'].append(UU_trans/SM_trans)
                    Pol_Trans[Samp]['T_DU']['Trans'].append(DU_trans/SM_trans)
                    Pol_Trans[Samp]['T_DD']['Trans'].append(DD_trans/SM_trans)
                    Pol_Trans[Samp]['T_UD']['Trans'].append(UD_trans/SM_trans)
                    Pol_Trans[Samp]['T_SM']['Trans_Cts'].append(SM_trans)
                counter += 1   
    return

def VSANS_ProcessTransCatalog(Trans, BlockBeam, DetectorPanel):
    #Uses VSANS_CalcABSTrans_BlockBeamList(trans_filenumber, BlockBeam, DetectorPanel) which uses
    #VSANS_MakeTransMask(filenumber, Config, DetectorPanel) and
    #VSANS_BlockedBeamCountsPerSecond_ListOfFiles(filelist, Config) and 
    #VSANS_AttenuatorTable(wavelength, attenuation)
    for Samp in Trans:
        for Config in Trans[Samp]['Config(s)']:
            BBList = [0]
            if Config in BlockBeam:
                if 'NA' not in BlockBeam[Config]['Trans']['File']:
                    BBList = BlockBeam[Config]['Trans']['File']
                elif 'NA' not in BlockBeam[Config]['Scatt']['File']:
                    BBList = BlockBeam[Config]['Scatt']['File']

            if 'NA' not in Trans[Samp]['Config(s)'][Config]['Unpol_Files']:
                for UNF in Trans[Samp]['Config(s)'][Config]['Unpol_Files']:
                    Unpol_trans, Unpol_trans_unc = VSANS_CalcABSTrans_BlockBeamList(UNF, BBList, DetectorPanel)
                    if 'NA' in Trans[Samp]['Config(s)'][Config]['Unpol_Trans_Cts']:
                        Trans[Samp]['Config(s)'][Config]['Unpol_Trans_Cts'] = [Unpol_trans]
                    else:
                        Trans[Samp]['Config(s)'][Config]['Unpol_Trans_Cts'].append(Unpol_trans)   
            if 'NA' not in Trans[Samp]['Config(s)'][Config]['U_Files']:
                    for UF in Trans[Samp]['Config(s)'][Config]['U_Files']:
                        Halfpol_trans, Halfpol_trans_unc = VSANS_CalcABSTrans_BlockBeamList(UF, BBList, DetectorPanel)
                        if 'NA' in Trans[Samp]['Config(s)'][Config]['U_Trans_Cts']:
                            Trans[Samp]['Config(s)'][Config]['U_Trans_Cts'] = [Halfpol_trans]
                        else:
                            Trans[Samp]['Config(s)'][Config]['U_Trans_Cts'].append(Halfpol_trans)
    return

def VSANS_ShareEmptyPolBeamScattCatalog(Scatt):

    for Sample_Name in Scatt:
        if str(Scatt[Sample_Name]['Intent']).find("Empty") != -1:
            for CF in Scatt[Sample_Name]['Config(s)']:
                if 'NA' in Scatt[Sample_Name]['Config(s)'][CF]['DD'] and 'NA' not in Scatt[Sample_Name]['Config(s)'][CF]['UU']:
                    Scatt[Sample_Name]['Config(s)'][CF]['DD'] = Scatt[Sample_Name]['Config(s)'][CF]['UU']
                    Scatt[Sample_Name]['Config(s)'][CF]['DD_Time'] = Scatt[Sample_Name]['Config(s)'][CF]['UU_Time']
                elif 'NA' in Scatt[Sample_Name]['Config(s)'][CF]['UU'] and 'NA' not in Scatt[Sample_Name]['Config(s)'][CF]['DD']:
                    Scatt[Sample_Name]['Config(s)'][CF]['UU'] = Scatt[Sample_Name]['Config(s)'][CF]['DD']
                    Scatt[Sample_Name]['Config(s)'][CF]['UU_Time'] = Scatt[Sample_Name]['Config(s)'][CF]['DD_Time']
                if 'NA' in Scatt[Sample_Name]['Config(s)'][CF]['UD'] and 'NA' not in Scatt[Sample_Name]['Config(s)'][CF]['DU']:
                    Scatt[Sample_Name]['Config(s)'][CF]['UD'] = Scatt[Sample_Name]['Config(s)'][CF]['DU']
                    Scatt[Sample_Name]['Config(s)'][CF]['UD_Time'] = Scatt[Sample_Name]['Config(s)'][CF]['DU_Time']
                elif 'NA' in Scatt[Sample_Name]['Config(s)'][CF]['DU'] and 'NA' not in Scatt[Sample_Name]['Config(s)'][CF]['UD']:
                    Scatt[Sample_Name]['Config(s)'][CF]['DU'] = Scatt[Sample_Name]['Config(s)'][CF]['UD']
                    Scatt[Sample_Name]['Config(s)'][CF]['DU_Time'] = Scatt[Sample_Name]['Config(s)'][CF]['UD_Time']

                if 'NA' in Scatt[Sample_Name]['Config(s)'][CF]['D'] and 'NA' not in Scatt[Sample_Name]['Config(s)'][CF]['U']:
                    Scatt[Sample_Name]['Config(s)'][CF]['D'] = Scatt[Sample_Name]['Config(s)'][CF]['U']
                elif 'NA' in Scatt[Sample_Name]['Config(s)'][CF]['U'] and 'NA' not in Scatt[Sample_Name]['Config(s)'][CF]['D']:
                    Scatt[Sample_Name]['Config(s)'][CF]['U'] = Scatt[Sample_Name]['Config(s)'][CF]['D']
                    
    return

def Plex_File(start_number):

    PlexData = {}
    filename = '0'
    Plex_file = [fn for fn in os.listdir(input_path) if fn.startswith("PLEX")]
    if len(Plex_file) >= 1:
        filename = str(Plex_file[0])
    fullpath = os.path.join(input_path, filename)
    if os.path.isfile(fullpath):
        print('Reading in ', filename)
        f = h5py.File(fullpath)
        for dshort in all_detectors:
            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
            if ConvertHighResToSubset > 0:
                if dshort == 'B':
                    data_subset = data[HighResMinX:HighResMaxX+1,HighResMinY:HighResMaxY+1]
                    PlexData[dshort] = data_subset
                else:
                    PlexData[dshort] = data
            else:
               PlexData[dshort] = data
    else:
        filenumber = start_number
        f = get_by_filenumber(filenumber)
        if f is not None:
            for dshort in all_detectors:
                data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                data_filler = np.ones_like(data)
                if ConvertHighResToSubset > 0:
                    if dshort == 'B':
                        data_subset = data_filler[HighResMinX:HighResMaxX+1,HighResMinY:HighResMaxY+1]
                        PlexData[dshort] = data_subset
                    else:
                        PlexData[dshort] = data_filler
                else:
                    PlexData[dshort] = data_filler
        print('Plex file not found; populated with ones instead')   
            
    return filename, PlexData

def SolidAngle_AllDetectors(representative_filenumber, Config):

    relevant_detectors = short_detectors
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors    
    
    Solid_Angle = {}
    f = get_by_filenumber(representative_filenumber)
    if f is not None:
        for dshort in relevant_detectors:
            detector_distance = f['entry/instrument/detector_{ds}/distance'.format(ds=dshort)][0]
            x_pixel_size = f['entry/instrument/detector_{ds}/x_pixel_size'.format(ds=dshort)][0]/10.0
            y_pixel_size = f['entry/instrument/detector_{ds}/y_pixel_size'.format(ds=dshort)][0]/10.0
            if dshort == 'MT' or dshort == 'MB' or dshort == 'FT' or dshort == 'FB':
                setback = f['entry/instrument/detector_{ds}/setback'.format(ds=dshort)][0]
            else:
                setback = 0
            realDistZ = detector_distance + setback
            theta_x_step = x_pixel_size / realDistZ
            theta_y_step = y_pixel_size / realDistZ
            Solid_Angle[dshort] = theta_x_step * theta_y_step

    return Solid_Angle

def QCalculation_AllDetectors(representative_filenumber, Config):

    relevant_detectors = short_detectors
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors

    Q_total = {}
    deltaQ = {}
    Qx = {}
    Qy = {}
    Qz = {}
    Q_perp_unc = {}
    Q_parl_unc = {}
    InPlaneAngleMap = {}
    TwoThetaAngleMap = {}
    twotheta_x = {}
    twotheta_y = {}
    twotheta_xmin = {}
    twotheta_xmax = {}
    twotheta_ymin = {}
    twotheta_ymax = {}
    dimXX = {}
    dimYY = {}   

    f = get_by_filenumber(representative_filenumber)
    if f is not None:
        for dshort in relevant_detectors:
            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
            Wavelength = f['entry/instrument/beam/monochromator/wavelength'][0]
            Wavelength_spread = f['entry/instrument/beam/monochromator/wavelength_spread'][0]
            dimX = f['entry/instrument/detector_{ds}/pixel_num_x'.format(ds=dshort)][0]
            dimY = f['entry/instrument/detector_{ds}/pixel_num_y'.format(ds=dshort)][0]
            dimXX[dshort] = f['entry/instrument/detector_{ds}/pixel_num_x'.format(ds=dshort)][0]
            dimYY[dshort] = f['entry/instrument/detector_{ds}/pixel_num_y'.format(ds=dshort)][0]
            beam_center_x = f['entry/instrument/detector_{ds}/beam_center_x'.format(ds=dshort)][0]
            beam_center_y = f['entry/instrument/detector_{ds}/beam_center_y'.format(ds=dshort)][0]
            beamstop_diameter = f['/entry/DAS_logs/C2BeamStop/diameter'][0]/10.0 #beam stop in cm; sits right in front of middle detector?
            detector_distance = f['entry/instrument/detector_{ds}/distance'.format(ds=dshort)][0]
            x_pixel_size = f['entry/instrument/detector_{ds}/x_pixel_size'.format(ds=dshort)][0]/10.0
            y_pixel_size = f['entry/instrument/detector_{ds}/y_pixel_size'.format(ds=dshort)][0]/10.0
            if dshort != 'B':
                panel_gap = f['entry/instrument/detector_{ds}/panel_gap'.format(ds=dshort)][0]/10.0
                coeffs = f['entry/instrument/detector_{ds}/spatial_calibration'.format(ds=dshort)][0][0]/10.0
            SampleApInternal = f['/entry/DAS_logs/geometry/internalSampleApertureHeight'][0] #internal sample aperture in cm
            SampleApExternal = f['/entry/DAS_logs/geometry/externalSampleApertureHeight'][0] #external sample aperture in cm
            SourceAp = f['/entry/DAS_logs/geometry/sourceApertureHeight'][0] #source aperture in cm, assumes circular aperture(?) #0.75, 1.5, or 3 for guides; otherwise 6 cm for >= 1 guides
            FrontDetToGateValve = f['/entry/DAS_logs/carriage/frontTrans'][0] #400
            MiddleDetToGateValve = f['/entry/DAS_logs/carriage/middleTrans'][0] #1650
            RearDetToGateValve = f['/entry/DAS_logs/carriage/rearTrans'][0]
            FrontDetToSample = f['/entry/DAS_logs/geometry/sampleToFrontLeftDetector'][0] #491.4
            MiddleDetToSample = f['/entry/DAS_logs/geometry/sampleToMiddleLeftDetector'][0] #1741.4
            RearDetToSample = f['/entry/DAS_logs/geometry/sampleToRearDetector'][0]
            SampleToSourceAp = f['/entry/DAS_logs/geometry/sourceApertureToSample'][0] #1490.6; "Calculated distance between sample and source aperture" in cm
            '''
            #GateValveToSample = f['/entry/DAS_logs/geometry/samplePositionOffset'][0] #e.g. 91.4; gate valve to sample in cm ("Hand-measured distance from the center of the table the sample is mounted on to the sample. A positive value means the sample is offset towards the guides.")
            #SampleToSampleAp = f['/entry/DAS_logs/geometry/SampleApertureOffset'][0] #e.g. 106.9; sample to sample aperture in cm ("Hand-measured distance between the Sample aperture and the sample.")            
            #SampleApToSourceAp = f['/entry/DAS_logs/geometry/sourceApertureToSampleAperture'][0] #1383.7; "Calculated distance between sample aperture and source aperture" in cm
            #Note gate valve to source aperture distances are based on the number of guides used:
            #0=2441; 1=2157; 2=1976; 3=1782; 4=1582; 5=1381; 6=1181; 7=980; 8=780; 9=579 in form of # guides=distance in cm
            '''
                
            if dshort == 'MT' or dshort == 'MB' or dshort == 'FT' or dshort == 'FB':
                setback = f['entry/instrument/detector_{ds}/setback'.format(ds=dshort)][0]
                vertical_offset = f['entry/instrument/detector_{ds}/vertical_offset'.format(ds=dshort)][0]
                lateral_offset = 0
            else:
                setback = 0
                vertical_offset = 0
                lateral_offset = f['entry/instrument/detector_{ds}/lateral_offset'.format(ds=dshort)][0]

            realDistZ = detector_distance + setback

            if dshort == 'B':
                realDistX =  x_pixel_size*(0.5)
                realDistY =  y_pixel_size*(0.5)
            else:
                position_key = dshort[1]
                if position_key == 'T':
                    realDistX =  coeffs
                    realDistY =  0.5 * y_pixel_size + vertical_offset + panel_gap/2.0
                elif position_key == 'B':
                    realDistX =  coeffs
                    realDistY =  vertical_offset - (dimY - 0.5)*y_pixel_size - panel_gap/2.0
                elif position_key == 'L':
                    realDistX =  lateral_offset - (dimX - 0.5)*x_pixel_size - panel_gap/2.0
                    realDistY =  coeffs
                elif position_key == 'R':
                    realDistX =  x_pixel_size*(0.5) + lateral_offset + panel_gap/2.0
                    realDistY =  coeffs

            X, Y = np.indices(data.shape)
            if dshort == 'B':
                x0_pos =  realDistX - beam_center_x*x_pixel_size + (X)*x_pixel_size 
                y0_pos =  realDistY - beam_center_y*y_pixel_size + (Y)*y_pixel_size
                x_min =  realDistX - beam_center_x*x_pixel_size - x_pixel_size 
                y_min =  realDistY - beam_center_y*y_pixel_size - y_pixel_size
                x_max =  realDistX - beam_center_x*x_pixel_size + (dimX)*x_pixel_size 
                y_max =  realDistY - beam_center_y*y_pixel_size + (dimY)*y_pixel_size
            else:
                x0_pos =  realDistX - beam_center_x + (X)*x_pixel_size 
                y0_pos =  realDistY - beam_center_y + (Y)*y_pixel_size
                x_min =  realDistX - beam_center_x - (1.0)*x_pixel_size
                y_min =  realDistY - beam_center_y - (1.0)*y_pixel_size
                x_max =  realDistX - beam_center_x + (dimX)*x_pixel_size
                y_max =  realDistY - beam_center_y + (dimY)*y_pixel_size
                
            if ConvertHighResToSubset > 0 and dshort == 'B':
                dimXX[dshort] = int(HighResMaxX - HighResMinX + 1)
                dimYY[dshort] = int(HighResMaxY - HighResMinY + 1)
                x0_pos = x0_pos[HighResMinX:HighResMaxX+1,HighResMinY:HighResMaxY+1]
                y0_pos = y0_pos[HighResMinX:HighResMaxX+1,HighResMinY:HighResMaxY+1]
                x_min =  realDistX - beam_center_x*x_pixel_size + HighResMinX*x_pixel_size 
                y_min =  realDistY - beam_center_y*y_pixel_size + HighResMinY*y_pixel_size
                x_max =  realDistX - beam_center_x*x_pixel_size + HighResMaxX*x_pixel_size 
                y_max =  realDistY - beam_center_y*y_pixel_size + HighResMaxY*y_pixel_size

            pad_factor = 1.0
            if dshort == "FL" or dshort == "ML":
                x_max = x_max + SampleApExternal/20.0
                x_max = x_max/pad_factor
            if dshort == "FR" or dshort == "MR":
                x_min = x_min - SampleApExternal/20.0
                x_min = x_min/pad_factor
            if dshort == "FB" or dshort == "MB":
                y_max = y_max + SampleApExternal/20.0
                y_max = y_max/pad_factor
            if dshort == "FT" or dshort == "MT":
                y_min = y_min - SampleApExternal/20.0
                y_min = y_min/pad_factor
                
            InPlane0_pos = np.sqrt(x0_pos**2 + y0_pos**2)
            twotheta = np.arctan2(InPlane0_pos,realDistZ)
            phi = np.arctan2(y0_pos,x0_pos)
            twotheta_x[dshort] = np.arctan2(x0_pos,realDistZ)
            twotheta_y[dshort] = np.arctan2(y0_pos,realDistZ)
            twotheta_xmin[dshort] = np.arctan2(x_min,realDistZ)
            twotheta_xmax[dshort] = np.arctan2(x_max,realDistZ)
            twotheta_ymin[dshort] = np.arctan2(y_min,realDistZ)
            twotheta_ymax[dshort] = np.arctan2(y_max,realDistZ)
            '''#Q resolution from J. of Appl. Cryst. 44, 1127-1129 (2011) and file:///C:/Users/kkrycka/Downloads/SANS_2D_Resolution.pdf where
            #there seems to be an extra factor of wavelength listed that shouldn't be there in (delta_wavelength/wavelength):'''
            carriage_key = dshort[0]
            if carriage_key == 'F':
                L2 = FrontDetToSample
            elif carriage_key == 'M':
                L2 = MiddleDetToSample
            elif dshort == 'B':
                L2 = RearDetToSample
            L1 = SampleToSourceAp
            Pix = 0.82
            R1 = SourceAp #source aperture radius in cm
            R2 = SampleApExternal #sample aperture radius in cm
            Inv_LPrime = 1.0/L1 + 1.0/L2
            k = 2*np.pi/Wavelength
            Sigma_D_Perp = np.sin(phi)*x_pixel_size + np.cos(phi)*y_pixel_size
            Sigma_D_Parl = np.cos(phi)*x_pixel_size + np.sin(phi)*y_pixel_size
            SigmaQPerpSqr = (k*k/12.0)*(3*np.power(R1/L1,2) + 3.0*np.power(R2*Inv_LPrime,2)+ np.power(Sigma_D_Perp/L2,2))
            SigmaQParlSqr = (k*k/12.0)*(3*np.power(R1/L1,2) + 3.0*np.power(R2*Inv_LPrime,2)+ np.power(Sigma_D_Parl/L2,2))
            R = np.sqrt(np.power(x0_pos,2)+np.power(y0_pos,2))
            Q0 = k*R/L2
            '''
            #If no gravity correction:
            #SigmaQParlSqr = SigmaQParlSqr + np.power(Q0,2)*np.power(Wavelength_spread/np.sqrt(6.0),2)
            #Else, if adding gravity correction:
            '''
            g = 981 #in cm/s^2
            m_div_h = 252.77 #in s cm^-2
            A = -0.5*981*L2*(L1+L2)*np.power(m_div_h , 2)
            WL = Wavelength*1E-8
            SigmaQParlSqr = SigmaQParlSqr + np.power(Wavelength_spread*k/(L2),2)*(R*R -4*A*np.sin(phi)*WL*WL + 4*A*A*np.power(WL,4))/6.0 #gravity correction makes vary little difference for wavelength spread < 20%
            '''VSANS IGOR 2D ASCII delta_Q seems to be way off the mark, but this 2D calculaation matches the VSANS circular average closely when pixels are converted to circular average...'''
            
            Q_total[dshort] = (4.0*np.pi/Wavelength)*np.sin(twotheta/2.0)
            QQ_total = (4.0*np.pi/Wavelength)*np.sin(twotheta/2.0)
            Qx[dshort] = QQ_total*np.cos(twotheta/2.0)*np.cos(phi)
            Qy[dshort] = QQ_total*np.cos(twotheta/2.0)*np.sin(phi)
            Qz[dshort] = QQ_total*np.sin(twotheta/2.0)     
            Q_perp_unc[dshort] = np.ones_like(Q_total[dshort])*np.sqrt(SigmaQPerpSqr)
            Q_parl_unc[dshort] = np.sqrt(SigmaQParlSqr)
            Phi_deg = phi*180.0/np.pi
            TwoTheta_deg = twotheta*180.0/np.pi
            InPlaneAngleMap[dshort] = Phi_deg
            TwoThetaAngleMap[dshort] = TwoTheta_deg
            '''#returns values between -180.0 degrees and +180.0 degrees'''

    Shadow_Mask = {}
    for dshort in relevant_detectors:
        Shadow = 1.2*np.ones_like(Qx[dshort])
        if dshort == 'FT' or dshort == 'FB':
            Shadow[twotheta_x[dshort] <= twotheta_xmax['FL']] = 0.0
            Shadow[twotheta_x[dshort] >= twotheta_xmin['FR']] = 0.0
        if dshort == "ML" or dshort == "MR":
            Shadow[twotheta_x[dshort] <= twotheta_xmax['FL']] = 0.0
            Shadow[twotheta_x[dshort] >= twotheta_xmin['FR']] = 0.0
            Shadow[twotheta_y[dshort] >= twotheta_ymin['FT']] = 0.0
            Shadow[twotheta_y[dshort] <= twotheta_ymax['FB']] = 0.0
        if dshort == "MT" or dshort == "MB":
            Shadow[twotheta_x[dshort] <= twotheta_xmax['FL']] = 0.0
            Shadow[twotheta_x[dshort] >= twotheta_xmin['FR']] = 0.0
            Shadow[twotheta_y[dshort] >= twotheta_ymin['FT']] = 0.0
            Shadow[twotheta_y[dshort] <= twotheta_ymax['FB']] = 0.0
            Shadow[twotheta_x[dshort] <= twotheta_xmax['ML']] = 0.0
            Shadow[twotheta_x[dshort] >= twotheta_xmin['MR']] = 0.0
        if dshort == "B":
            Shadow[twotheta_x[dshort] <= twotheta_xmax['FL']] = 0.0
            Shadow[twotheta_x[dshort] >= twotheta_xmin['FR']] = 0.0
            Shadow[twotheta_y[dshort] >= twotheta_ymin['FT']] = 0.0
            Shadow[twotheta_y[dshort] <= twotheta_ymax['FB']] = 0.0
            Shadow[twotheta_x[dshort] <= twotheta_xmax['ML']] = 0.0
            Shadow[twotheta_x[dshort] >= twotheta_xmin['MR']] = 0.0
            Shadow[twotheta_y[dshort] >= twotheta_ymin['MT']] = 0.0
            Shadow[twotheta_y[dshort] <= twotheta_ymax['MB']] = 0.0

        Shadow_Mask[dshort] = Shadow
        #print(Config, dshort, "sum", np.sum(Shadow_Mask[dshort]))

    return Qx, Qy, Qz, Q_total, Q_perp_unc, Q_parl_unc, InPlaneAngleMap, dimXX, dimYY, Shadow_Mask

def SectorMask_AllDetectors(InPlaneAngleMap, PrimaryAngle, AngleWidth, BothSides):

    SectorMask = {}
    relevant_detectors = short_detectors
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors
    for dshort in relevant_detectors:
        Angles = InPlaneAngleMap[dshort]
        SM = np.zeros_like(Angles)

        if PrimaryAngle > 180.0:
            PrimaryAngle = PrimaryAngle - 360.0
        if PrimaryAngle < -180.0:
            PrimaryAngle = PrimaryAngle + 360.0
        SM[np.absolute(Angles - PrimaryAngle) <= AngleWidth] = 1.0
        SM[np.absolute(Angles + 360 - PrimaryAngle) <= AngleWidth] = 1.0
        SM[np.absolute(Angles - 360 - PrimaryAngle) <= AngleWidth] = 1.0
        if BothSides >= 1:
            SecondaryAngle = PrimaryAngle + 180
            if SecondaryAngle > 180.0:
                SecondaryAngle = SecondaryAngle - 360.0
            if SecondaryAngle < -180.0:
                SecondaryAngle = SecondaryAngle + 360.0
            SM[np.absolute(Angles - SecondaryAngle) <= AngleWidth] = 1.0
            SM[np.absolute(Angles + 360 - SecondaryAngle) <= AngleWidth] = 1.0
            SM[np.absolute(Angles - 360 - SecondaryAngle) <= AngleWidth] = 1.0
            
        SectorMask[dshort] = SM
    return SectorMask
            
def He3Decay_func(t, p, gamma):
    return p * np.exp(-t / gamma)

def HE3_Pol_AtGivenTime(entry_time, HE3_Cell_Summary):
    '''
    #Predefine HE3_Cell_Summary[HE3_Trans[entry]['Insert_time']] = {'Atomic_P0' : P0, 'Gamma(hours)' : gamma, 'Mu' : Mu, 'Te' : Te}
    #He3Decay_func must be predefined
    '''
    counter = 0
    for time in HE3_Cell_Summary:
        if counter == 0:
            holder_time = time
            counter += 1
        if entry_time >= time:
            holder_time = time
        if entry_time < time:
            break
    delta_time = entry_time - holder_time     
    P0 = HE3_Cell_Summary[holder_time]['Atomic_P0']
    gamma = HE3_Cell_Summary[holder_time]['Gamma(hours)']
    Mu = HE3_Cell_Summary[holder_time]['Mu']
    Te = HE3_Cell_Summary[holder_time]['Te']
    AtomicPol = P0 * np.exp(-delta_time / gamma)
    NeutronPol = np.tanh(Mu * AtomicPol)
    UnpolHE3Trans = Te * np.exp(-Mu)*np.cosh(Mu * AtomicPol)
    T_MAJ = Te * np.exp(-Mu*(1.0 - AtomicPol))
    T_MIN = Te * np.exp(-Mu*(1.0 + AtomicPol))
        
    return NeutronPol, UnpolHE3Trans, T_MAJ, T_MIN

def HE3_DecayCurves(HE3_Trans):
    '''
    #Uses predefined He3Decay_func
    #Creates and returns HE3_Cell_Summary
    '''
    HE3_Cell_Summary = {}
    entry_number = 0
    for entry in HE3_Trans:
        entry_number += 1
        Mu = HE3_Trans[entry]['Mu']
        Te = HE3_Trans[entry]['Te']
        xdata = np.array(HE3_Trans[entry]['Elasped_time'])
        trans_data = np.array(HE3_Trans[entry]['Transmission'])
        ydata = np.arccosh(np.array(trans_data)/(np.e**(-Mu)*Te))/Mu
        if xdata.size < 2:
            P0 = ydata[0]
            gamma = 1000.0
            '''#assumes no appreciable time decay until more data obtained'''
            PCell0 = np.tanh(Mu * P0)
            P0_Unc = 'NA'
            gamma_Unc = 'NA'
            PCell0_Unc = 'NA'
        else:
            popt, pcov = curve_fit(He3Decay_func, xdata, ydata)
            P0, gamma = popt
            P0_Unc, gamma_Unc = np.sqrt(np.diag(pcov))
            PCell0 = np.tanh(Mu * P0)
            PCell0_Max = np.tanh(Mu * (P0+P0_Unc))
            PCell0_Min = np.tanh(Mu * (P0-P0_Unc))
            PCell0_Unc = PCell0_Max - PCell0_Min

        Name = HE3_Trans[entry]['Cell_name'][0]
        HE3_Cell_Summary[HE3_Trans[entry]['Insert_time']] = {'Atomic_P0' : P0, 'Atomic_P0_Unc' : P0_Unc, 'Gamma(hours)' : gamma, 'Gamma_Unc' : gamma_Unc, 'Mu' : Mu, 'Te' : Te, 'Name' : Name, 'Neutron_P0' : PCell0, 'Neutron_P0_Unc' : PCell0_Unc}
        print('He3Cell Summary for Cell Identity', HE3_Trans[entry]['Cell_name'][0])
        print('PolCell0: ', PCell0, '+/-', PCell0_Unc)
        print('AtomicPol0: ', P0, '+/-', P0_Unc)
        print('Gamma (hours): ', gamma, '+/-', gamma_Unc)
        print('     ')

        if xdata.size >= 2:
            print('Graphing He3 decay curve....(close generated plot to continue)')
            fit = He3Decay_func(xdata, popt[0], popt[1])
            fit_max = He3Decay_func(xdata, popt[0] + P0_Unc, popt[1] + gamma_Unc)
            fit_min = He3Decay_func(xdata, popt[0] - P0_Unc, popt[1] - gamma_Unc)
            fig = plt.figure()
            plt.plot(xdata, ydata, 'b*', label='data')
            plt.plot(xdata, fit_max, 'r-', label='fit of data (upper bounds)')
            plt.plot(xdata, fit, 'y-', label='fit of data (best)')
            plt.plot(xdata, fit_min, 'c-', label='fit of data (lower bounds)')
            plt.xlabel('time (hours)')
            plt.ylabel('3He atomic polarization')
            plt.title('He3 Cell Decay')
            plt.legend()
            fig.savefig(save_path + 'He3Curve_AtomicPolarization_Cell{cell}.png'.format(cell = entry))
            plt.pause(2)
            plt.close()

        if xdata.size >= 2 and entry_number == len(HE3_Trans):
            print('Graphing current and projected decay curves....(close generated plot to continue)')
            TMAJ_data = Te * np.exp(-Mu*(1.0 - ydata))
            TMIN_data = Te * np.exp(-Mu*(1.0 + ydata))
            xdatalonger = HE3_Trans[entry]['Elasped_time']
            L = len(xdata)
            last_time = xdata[L-1]
            for i in range(49):
                extra_time = last_time + i*1
                xdatalonger.append(extra_time)
            xdataextended = np.array(xdatalonger)
            AtomicPol_fitlonger = He3Decay_func(xdataextended, popt[0], popt[1])
            TMAJ_fit = Te * np.exp(-Mu*(1.0 - AtomicPol_fitlonger))
            TMIN_fit = Te * np.exp(-Mu*(1.0 + AtomicPol_fitlonger))
            
            fig = plt.figure()
            plt.plot(xdata, TMAJ_data, 'b*', label='T_MAJ data')
            plt.plot(xdataextended, TMAJ_fit, 'c-', label='T_MAJ predicted')

            plt.plot(xdata, TMIN_data, 'r*', label='T_MIN data')
            plt.plot(xdataextended, TMIN_fit, 'm-', label='T_MIN predicted')
            
            plt.xlabel('time (hours)')
            plt.ylabel('Spin Transmission')
            plt.title('Predicted He3 Cell Transmission')
            plt.legend()
            fig.savefig(save_path + 'He3PredictedDecayCurve_{cell}.png'.format(cell = entry))
            plt.pause(2)
            plt.close()

    return HE3_Cell_Summary

def vSANS_PolarizationSupermirrorAndFlipper(Pol_Trans, HE3_Cell_Summary, UsePolCorr):
    #Uses time of measurement from Pol_Trans and cell history from HE3_Cell_Summary.
    #Saves PSM and PF values into Pol_Trans.
    #Uses prefefined HE3_Pol_AtGivenTime function.
    #Note: The vSANS RF Flipper polarization has been measured at 1.0 and is, thus, set.
    
    for ID in Pol_Trans:
        if 'Meas_Time' in Pol_Trans[ID]['T_UU']:
            for Time in Pol_Trans[ID]['T_UU']['Meas_Time']:
                NP, UT, T_MAJ, T_MIN = HE3_Pol_AtGivenTime(Time, HE3_Cell_Summary)
                if 'Neutron_Pol' not in Pol_Trans[ID]['T_UU']:
                    Pol_Trans[ID]['T_UU']['Neutron_Pol'] = [NP]
                    Pol_Trans[ID]['T_UU']['Unpol_Trans'] = [UT]
                else:
                    Pol_Trans[ID]['T_UU']['Neutron_Pol'].append(NP)
                    Pol_Trans[ID]['T_UU']['Unpol_Trans'].append(UT)
            for Time in Pol_Trans[ID]['T_DD']['Meas_Time']:
                NP, UT, T_MAJ, T_MIN = HE3_Pol_AtGivenTime(Time, HE3_Cell_Summary)
                if 'Neutron_Pol' not in Pol_Trans[ID]['T_DD']:
                    Pol_Trans[ID]['T_DD']['Neutron_Pol'] = [NP]
                    Pol_Trans[ID]['T_DD']['Unpol_Trans'] = [UT]
                else:
                    Pol_Trans[ID]['T_DD']['Neutron_Pol'].append(NP)
                    Pol_Trans[ID]['T_DD']['Unpol_Trans'].append(UT)       
            for Time in Pol_Trans[ID]['T_DU']['Meas_Time']:
                NP, UT, T_MAJ, T_MIN = HE3_Pol_AtGivenTime(Time, HE3_Cell_Summary)
                if 'Neutron_Pol' not in Pol_Trans[ID]['T_DU']:
                    Pol_Trans[ID]['T_DU']['Neutron_Pol'] = [NP]
                    Pol_Trans[ID]['T_DU']['Unpol_Trans'] = [UT]
                else:
                    Pol_Trans[ID]['T_DU']['Neutron_Pol'].append(NP)
                    Pol_Trans[ID]['T_DU']['Unpol_Trans'].append(UT)     
            for Time in Pol_Trans[ID]['T_UD']['Meas_Time']:
                NP, UT,T_MAJ, T_MIN = HE3_Pol_AtGivenTime(Time, HE3_Cell_Summary)
                if 'Neutron_Pol' not in Pol_Trans[ID]['T_UD']:
                    Pol_Trans[ID]['T_UD']['Neutron_Pol'] = [NP]
                    Pol_Trans[ID]['T_UD']['Unpol_Trans'] = [UT]
                else:
                    Pol_Trans[ID]['T_UD']['Neutron_Pol'].append(NP)
                    Pol_Trans[ID]['T_UD']['Unpol_Trans'].append(UT)

    for ID in Pol_Trans:
        if 'Neutron_Pol' in Pol_Trans[ID]['T_UU']:
            ABS = np.array(Pol_Trans[ID]['T_SM']['Trans_Cts'])
            Pol_Trans[ID]['AbsScale'] = np.average(ABS)

            UU = np.array(Pol_Trans[ID]['T_UU']['Trans'])
            UU_UnpolHe3Trans = np.array(Pol_Trans[ID]['T_UU']['Unpol_Trans'])
            UU_NeutronPol = np.array(Pol_Trans[ID]['T_UU']['Neutron_Pol'])
            DD = np.array(Pol_Trans[ID]['T_DD']['Trans'])
            DD_UnpolHe3Trans = np.array(Pol_Trans[ID]['T_DD']['Unpol_Trans'])
            DD_NeutronPol = np.array(Pol_Trans[ID]['T_DD']['Neutron_Pol'])
            UD = np.array(Pol_Trans[ID]['T_UD']['Trans'])
            UD_UnpolHe3Trans = np.array(Pol_Trans[ID]['T_UD']['Unpol_Trans'])
            UD_NeutronPol = np.array(Pol_Trans[ID]['T_UD']['Neutron_Pol'])
            DU = np.array(Pol_Trans[ID]['T_DU']['Trans'])
            DU_UnpolHe3Trans = np.array(Pol_Trans[ID]['T_DU']['Unpol_Trans'])
            DU_NeutronPol = np.array(Pol_Trans[ID]['T_DU']['Neutron_Pol'])
            print('  ')
            print(ID)
            print('UU, DU, DD, UD Trans:', int(np.average(UU)*10000)/10000, " " , int(np.average(DU)*10000)/10000, " ", int(np.average(DD)*10000)/10000, " ", int(np.average(UD)*10000)/10000)
            NPAve = 0.25*(np.average(UU_NeutronPol) + np.average(DU_NeutronPol) + np.average(DD_NeutronPol) + np.average(UD_NeutronPol))
            print('3He Pol (Ave.)', NPAve)
            
            PF = 1.00
            Pol_Trans[ID]['P_F'] = np.average(PF)
            PSMUU = (UU/UU_UnpolHe3Trans - 1.0)/(UU_NeutronPol)
            PSMDD = (DD/DD_UnpolHe3Trans - 1.0)/(DD_NeutronPol)
            PSMUD = (1.0 - UD/UD_UnpolHe3Trans)/(UD_NeutronPol)
            PSMDU = (1.0 - DU/DU_UnpolHe3Trans)/(DU_NeutronPol)
            PSM_Ave = 0.25*(np.average(PSMUU) + np.average(PSMDD) + np.average(PSMUD) + np.average(PSMDU))
            Pol_Trans[ID]['P_SM'] = np.average(PSM_Ave)
            print('Sample Depol * PSM', Pol_Trans[ID]['P_SM'])
            print('Flipping ratios (UU/DU, DD/UD):', int(10000*np.average(UU)/np.average(DU))/10000, int(10000*np.average(DD)/np.average(UD))/10000)
            
            if UsePolCorr == 0:
                '''#0 Means no, turn it off'''
                Pol_Trans[ID]['P_SM'] = 1.0
                Pol_Trans[ID]['P_F'] = 1.0
                print('Manually reset P_SM and P_F to unity')

    print(" ")
    return

def AbsScale(ScattType, Sample, Config, BlockBeam_per_second, Solid_Angle, Plex, Scatt, Trans):

    Scaled_Data = {}
    UncScaled_Data = {}
    masks = {}
    BB = {}

    relevant_detectors = short_detectors
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors

    if Sample in Scatt:
        if Config in Scatt[Sample]['Config(s)']:
            Number_Files = 1.0*len(Scatt[Sample]['Config(s)'][Config][ScattType])

            if ScattType == 'UU' or ScattType == 'DU'  or ScattType == 'DD'  or ScattType == 'UD' or ScattType == 'U' or ScattType == 'D':
                TransType = 'U_Trans_Cts'
                TransTypeAlt = 'Unpol_Trans_Cts'
            elif ScattType == 'Unpol':
                TransType = 'Unpol_Trans_Cts'
                TransTypeAlt = 'U_Trans_Cts'
            else:
                print('There is a problem with the Scatting Type requested in the Absobulte Scaling Function')
                
            ABS_Scale = 1.0
            if Sample in Trans and str(Scatt[Sample]['Config(s)'][Config][ScattType]).find('NA') == -1:
                if Sample in Trans:
                    if Config in Trans[Sample]['Config(s)']:
                        if TransType in Trans[Sample]['Config(s)'][Config] and str(Trans[Sample]['Config(s)'][Config][TransType]).find("NA") == -1 :
                            ABS_Scale = np.average(np.array(Trans[Sample]['Config(s)'][Config][TransType]))
                        elif TransTypeAlt in Trans[Sample]['Config(s)'][Config] and str(Trans[Sample]['Config(s)'][Config]).find("NA") == -1 :
                            ABS_Scale = np.average(np.array(Trans[Sample]['Config(s)'][Config][TransTypeAlt]))
                            
                '''
                #Calculating an average block beam counts per pixel and time (seems to work better than a pixel-by-pixel subtraction,
                at least for shorter count times)'''
                
            for dshort in relevant_detectors:
                Holder =  np.array(BlockBeam_per_second[dshort])
                '''Optional:
                if Config in Masks:
                    if 'Scatt_WithSolenoidss' in Masks[Config]:   
                        masks[dshort] = Masks[Config]['Scatt_WithSolenoid'][dshort]
                    elif 'Scatt_Standardss' in Masks[Config]:
                        masks[dshort] = Masks[Config]['Scatt_Standard'][dshort]
                    else:
                        masks[dshort] = np.ones_like(Holder)
                else:
                    masks[dshort] = np.ones_like(Holder)
                '''
                masks[dshort] = np.ones_like(Holder)
                Sum = np.sum(Holder[masks[dshort] > 0])
                Pixels = np.sum(masks[dshort])
                Unc = np.sqrt(Sum)/Pixels
                Ave = np.average(Holder[masks[dshort] > 0])
                BB[dshort] = Ave
                if ConvertHighResToSubset > 0 and dshort == 'B':
                    bb_holder = Holder[HighResMinX:HighResMaxX+1,HighResMinY:HighResMaxY+1]
                    bb_sum = np.sum(bb_holder)
                    bb_ave = np.average(Holder[HighResMinX:HighResMaxX+1,HighResMinY:HighResMaxY+1])
                    BB[dshort] = (bb_holder)/HighResGain # Better to subtract BB pixel-by-pixel than average for HighRes detector


            He3Glass_Trans = 1.0
            filecounter = 0
            if str(Scatt[Sample]['Config(s)'][Config][ScattType]).find('NA') != -1:
                Scaled_Data = 'NA'
                UncScaled_Data = 'NA'
            else:
                for filenumber in Scatt[Sample]['Config(s)'][Config][ScattType]:
                    filecounter += 1
                    f = get_by_filenumber(filenumber)
                    if f is not None:
                        MonCounts = f['entry/control/monitor_counts'][0]
                        Count_time = f['entry/collection_time'][0]
                        He3Glass_Trans = 1.0
                        if ScattType == 'UU' or ScattType == 'DU'  or ScattType == 'DD'  or ScattType == 'UD':
                            if YesNoManualHe3Entry == 0:
                                He3Glass_Trans = f['/entry/DAS_logs/backPolarization/glassTransmission'][0]
                            else:
                                He3Glass_Trans = TeValues[0]
                        for dshort in relevant_detectors:
                            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            unc = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            if ConvertHighResToSubset > 0 and dshort == 'B':
                                data_holder = data/HighResGain
                                data = data_holder[HighResMinX:HighResMaxX+1,HighResMinY:HighResMaxY+1]
                                unc = data_holder[HighResMinX:HighResMaxX+1,HighResMinY:HighResMaxY+1]
                            data = (data - Count_time*BB[dshort])/(Number_Files*Plex[dshort]*Solid_Angle[dshort])
                            if filecounter < 2:
                                Scaled_Data[dshort] = ((1E8/MonCounts)/(ABS_Scale*He3Glass_Trans))*data
                                UncScaled_Data[dshort] = unc
                            else:
                                Scaled_Data[dshort] += ((1E8/MonCounts)/(ABS_Scale*He3Glass_Trans))*data
                                UncScaled_Data[dshort] += unc           
                for dshort in relevant_detectors:
                    UncScaled_Data[dshort] = np.sqrt(UncScaled_Data[dshort])*((1E8/MonCounts)/(ABS_Scale*He3Glass_Trans))/(Number_Files*Plex[dshort]*Solid_Angle[dshort])

        else:
            Scaled_Data = 'NA'
            UncScaled_Data = 'NA'
                
    return Scaled_Data, UncScaled_Data

def vSANS_BestSuperMirrorPolarizationValue(Starting_PSM, YesNoBypassBestGuessPSM, Pol_Trans):
    
    Measured_PSM = [Starting_PSM]
    if YesNoBypassBestGuessPSM > 0:
        for Sample in Pol_Trans:              
            if 'P_SM' in Pol_Trans[Sample]:
                Measured_PSM.append(Pol_Trans[Sample]['P_SM'])
    Truest_PSM = np.amax(Measured_PSM)
    print('Best measured PSM value is', Truest_PSM)
    if Truest_PSM > 1:
        Truest_PSM = 1.0
        print('Best PSM value set to 1.0')
    print(" ")

    return Truest_PSM

def vSANS_PolCorrScattFiles(BestPSM, dimXX, dimYY, Sample, Config, Scatt, Trans, Pol_Trans, UUScaledData, DUScaledData, DDScaledData, UDScaledData, UUScaledData_Unc, DUScaledData_Unc, DDScaledData_Unc, UDScaledData_Unc):

    Scaled_Data = np.zeros((8,4,6144))
    UncScaled_Data = np.zeros((8,4,6144))

    relevant_detectors = short_detectors

    Det_counter = 0
    for dshort in relevant_detectors:
        UUD = np.array(UUScaledData[dshort])
        Scaled_Data[Det_counter][0][:] += UUD.flatten()
        
        DUD = np.array(DUScaledData[dshort])
        Scaled_Data[Det_counter][1][:] += DUD.flatten()

        DDD = np.array(DDScaledData[dshort])
        Scaled_Data[Det_counter][2][:] += DDD.flatten()

        UDD = np.array(UDScaledData[dshort])
        Scaled_Data[Det_counter][3][:] += UDD.flatten()

        UUD_Unc = np.array(UUScaledData_Unc[dshort])
        UncScaled_Data[Det_counter][0][:] += UUD_Unc.flatten()
        
        DUD_Unc = np.array(DUScaledData_Unc[dshort])
        UncScaled_Data[Det_counter][1][:] += DUD_Unc.flatten()

        DDD_Unc = np.array(DDScaledData_Unc[dshort])
        UncScaled_Data[Det_counter][2][:] += DDD_Unc.flatten()

        UDD_Unc = np.array(UDScaledData_Unc[dshort])
        UncScaled_Data[Det_counter][3][:] += UDD_Unc.flatten()

        Det_counter += 1

    '''#Full-Pol Reduction:'''
    PolCorr_UU = {}
    PolCorr_DU = {}
    PolCorr_DD = {}
    PolCorr_UD = {}
    PolCorr_UU_Unc = {}
    PolCorr_DU_Unc = {}
    PolCorr_DD_Unc = {}
    PolCorr_UD_Unc = {}

    Pol_Efficiency = np.zeros((4,4))
    Pol_Efficiency_V2 = np.zeros((4,4))
    HE3_Efficiency = np.zeros((4,4))
    PolCorr_AllDetectors = {}
    HE3Corr_AllDetectors = {}
    Uncertainty_PolCorr_AllDetectors = {}
    Have_FullPol = 0
    if Sample in Trans and str(Scatt[Sample]['Config(s)'][Config]['UU']).find('NA') == -1 and str(Scatt[Sample]['Config(s)'][Config]['DU']).find('NA') == -1 and str(Scatt[Sample]['Config(s)'][Config]['DD']).find('NA') == -1 and str(Scatt[Sample]['Config(s)'][Config]['UD']).find('NA') == -1:
        Have_FullPol = 1

        if Sample in Pol_Trans:
            PSM = Pol_Trans[Sample]['P_SM']
            PF = Pol_Trans[Sample]['P_F']
            print(Sample, Config, 'PSM is', PSM)
            if UsePolCorr >= 1:
                Have_FullPol = 2
        else:
            print(Sample, Config, 'missing P_F and P_SM; will proceed without pol-correction!')
            PF = 1.0
            PSM = 1.0
        '''#Calculating an average block beam counts per pixel and time (seems to work better than a pixel-by-pixel subtraction,
        at least for shorter count times)'''

        Number_UU = 1.0*len(Scatt[Sample]['Config(s)'][Config]["UU"])
        Number_DU = 1.0*len(Scatt[Sample]['Config(s)'][Config]["DU"])
        Number_DD = 1.0*len(Scatt[Sample]['Config(s)'][Config]["DD"])
        Number_UD = 1.0*len(Scatt[Sample]['Config(s)'][Config]["UD"])      
            
        Scatt_Type = ["UU", "DU", "DD", "UD"]
        for type in Scatt_Type:
            type_time = type + "_Time"
            filenumber_counter = 0
            for filenumber in Scatt[Sample]['Config(s)'][Config][type]:
                f = get_by_filenumber(representative_filenumber)
                if f is not None:
                    entry = Scatt[Sample]['Config(s)'][Config][type_time][filenumber_counter]
                    NP, UT, T_MAJ, T_MIN = HE3_Pol_AtGivenTime(entry, HE3_Cell_Summary)
                    C = NP
                    S = BestPSM
                    if PSM < Minimum_PSM:
                        PSM = Minimum_PSM
                    '''#0.9985 is the highest I've recently gotten at 5.5 Ang from EuSe 60 nm 0.95 V and 2.0 K'''
                    X = np.sqrt(PSM/S)
                    Y = X
                    SX = PSM
                    if type == "UU":
                        CrossSection_Index = 0
                        UT = UT / Number_UU
                        Pol_Efficiency[CrossSection_Index][:] += [(C*(S*X*Y + Y) + S*X + 1)*UT, (C*(-S*X*Y + Y) - S*X + 1)*UT, (C*(S*X*Y - Y) - S*X + 1)*UT, (C*(-S*X*Y - Y) + S*X + 1)*UT]
                        Pol_Efficiency_V2[CrossSection_Index][:] += [(C*(SX + 1) + SX + 1)*UT, (C*(-SX + 1) - SX + 1)*UT, (C*(SX - 1) - SX + 1)*UT, (C*(-SX - 1) + SX + 1)*UT]
                        HE3_Efficiency[CrossSection_Index][:] += [ UT, 0.0, 0.0, 0.0]
                    elif type == "DU":
                        CrossSection_Index = 1
                        UT = UT / Number_DU
                        Pol_Efficiency[CrossSection_Index][:] += [(C*(-S*X*Y + Y) - S*X + 1)*UT, (C*(S*X*Y + Y) + S*X + 1)*UT, (C*(-S*X*Y - Y) + S*X + 1)*UT, (C*(S*X*Y - Y) - S*X + 1)*UT]
                        Pol_Efficiency_V2[CrossSection_Index][:] += [(C*(-SX + 1) - SX + 1)*UT, (C*(SX + 1) + SX + 1)*UT, (C*(-SX - 1) + SX + 1)*UT, (C*(SX - 1) - SX + 1)*UT]
                        HE3_Efficiency[CrossSection_Index][:] += [ 0.0, UT, 0.0, 0.0]
                    elif type == "DD":
                        CrossSection_Index = 2
                        UT = UT / Number_DD
                        Pol_Efficiency[CrossSection_Index][:] += [(C*(S*X*Y - Y) - S*X + 1)*UT, (C*(-S*X*Y - Y) + S*X + 1)*UT, (C*(S*X*Y + Y) + S*X + 1)*UT, (C*(-S*X*Y + Y) - S*X + 1)*UT]
                        Pol_Efficiency_V2[CrossSection_Index][:] += [(C*(SX - 1) - SX + 1)*UT, (C*(-SX - 1) + SX + 1)*UT, (C*(SX + 1) + SX + 1)*UT, (C*(-SX + 1) - SX + 1)*UT]
                        HE3_Efficiency[CrossSection_Index][:] += [ 0.0, 0.0, UT, 0.0]
                    elif type == "UD":
                        CrossSection_Index = 3
                        UT = UT / Number_UD
                        Pol_Efficiency[CrossSection_Index][:] += [(C*(-S*X*Y - Y) + S*X + 1)*UT, (C*(S*X*Y - Y) - S*X + 1)*UT, (C*(-S*X*Y + Y) - S*X + 1)*UT, (C*(S*X*Y + Y) + S*X + 1)*UT]
                        Pol_Efficiency_V2[CrossSection_Index][:] += [(C*(-SX - 1) + SX + 1)*UT, (C*(SX - 1) - SX + 1)*UT, (C*(-SX + 1) - SX + 1)*UT, (C*(SX + 1) + SX + 1)*UT]
                        HE3_Efficiency[CrossSection_Index][:] += [ 0.0, 0.0, 0.0, UT]

        Prefactor = inv(Pol_Efficiency)
        if UsePolCorr == 1 and He3CorrectionType == 0: #old way with X depol before sample and Y depol after sample = 1
            Prefactor = inv(Pol_Efficiency_V2)
        if UsePolCorr == 0:
            Prefactor = inv(4.0*HE3_Efficiency)
            
        if str(Config).find('CvB') != -1:
            HRX = int(dimXX['B'])
            HRY = int(dimYY['B'])
            highrespixels = HRX*HRY
            RearScaled_Data = np.zeros((4, highrespixels))
            UncRearScaled_Data = np.zeros((4, highrespixels))
            
            UUR = np.array(UUScaledData['B'])
            RearScaled_Data[0][:] += UUR.flatten()
            DUR = np.array(DUScaledData['B'])
            RearScaled_Data[1][:] += DUR.flatten()
            DDR = np.array(DDScaledData['B'])
            RearScaled_Data[2][:] += DDR.flatten()
            UDR = np.array(UDScaledData['B'])
            RearScaled_Data[3][:] += UDR.flatten()
            UncRearScaled_Data[0][:] = RearScaled_Data[0][:]
            UncRearScaled_Data[1][:] = RearScaled_Data[1][:]
            UncRearScaled_Data[2][:] = RearScaled_Data[2][:]
            UncRearScaled_Data[3][:] = RearScaled_Data[3][:]

            BackPolCorr = np.dot(Prefactor, RearScaled_Data)
            BackUncertainty_PolCorr = UncRearScaled_Data
            
            PolCorr_UU['B'] = BackPolCorr[0][:][:].reshape((HRX, HRY))
            PolCorr_UU_Unc['B'] = BackUncertainty_PolCorr[0][:][:].reshape((HRX, HRY))
            PolCorr_DU['B'] = BackPolCorr[1][:][:].reshape((HRX, HRY))
            PolCorr_DU_Unc['B'] = BackUncertainty_PolCorr[1][:][:].reshape((HRX, HRY))
            PolCorr_DD['B'] = BackPolCorr[2][:][:].reshape((HRX, HRY))
            PolCorr_DD_Unc['B'] = BackUncertainty_PolCorr[2][:][:].reshape((HRX, HRY))
            PolCorr_UD['B'] = BackPolCorr[3][:][:].reshape((HRX, HRY))
            PolCorr_UD_Unc['B'] = BackUncertainty_PolCorr[3][:][:].reshape((HRX, HRY))

        
        Det_Index = 0
        for dshort in relevant_detectors:
            UncData_Per_Detector = UncScaled_Data[Det_Index][:][:]
            Data_Per_Detector = Scaled_Data[Det_Index][:][:]
            
            PolCorr_Data = np.dot(2.0*Prefactor, Data_Per_Detector)
            '''
            #Below is the code that allows true matrix error propagation, but it takes a while...so may want to optimize more before implementing.
            #Also will need to uncomment from uncertainties import unumpy (top).
            Data_Per_Detector2 = unumpy.umatrix(Scaled_Data[Det_Index][:][:], UncScaled_Data[Det_Index][:][:])
            PolCorr_Data2 = np.dot(Prefactor, Data_Per_Detector2)
            PolCorr_Data = unumpy.nominal_values(PolCorr_Data2)
            PolCorr_Unc = unumpy.std_devs(PolCorr_Data2)
            '''
            PolCorr_AllDetectors[dshort] = PolCorr_Data
            Uncertainty_PolCorr_AllDetectors[dshort] = UncData_Per_Detector
            Det_Index += 1

            dimX = dimXX[dshort]
            dimY = dimYY[dshort]
            PolCorr_UU[dshort] = PolCorr_AllDetectors[dshort][0][:][:].reshape((dimX, dimY))
            PolCorr_DU[dshort] = PolCorr_AllDetectors[dshort][1][:][:].reshape((dimX, dimY))
            PolCorr_DD[dshort] = PolCorr_AllDetectors[dshort][2][:][:].reshape((dimX, dimY))
            PolCorr_UD[dshort] = PolCorr_AllDetectors[dshort][3][:][:].reshape((dimX, dimY))

            PolCorr_UU_Unc[dshort] = Uncertainty_PolCorr_AllDetectors[dshort][0][:][:].reshape((dimX, dimY))
            PolCorr_DU_Unc[dshort] = Uncertainty_PolCorr_AllDetectors[dshort][1][:][:].reshape((dimX, dimY))
            PolCorr_DD_Unc[dshort] = Uncertainty_PolCorr_AllDetectors[dshort][2][:][:].reshape((dimX, dimY))
            PolCorr_UD_Unc[dshort] = Uncertainty_PolCorr_AllDetectors[dshort][3][:][:].reshape((dimX, dimY))

    return Have_FullPol, PolCorr_UU, PolCorr_DU, PolCorr_DD, PolCorr_UD, PolCorr_UU_Unc, PolCorr_DU_Unc, PolCorr_DD_Unc, PolCorr_UD_Unc

def MinMaxQ(Q_total, Config):
    
    MinQ1 = np.amin(Q_total['MR'])
    MinQ2 = np.amin(Q_total['ML'])
    MinQ3 = np.amin(Q_total['MT'])
    MinQ4 = np.amin(Q_total['MB'])
    MinQs = np.array([MinQ1, MinQ2, MinQ3, MinQ4])
    MinQ_Middle = np.amin(MinQs)
    
    MaxQ1 = np.amax(Q_total['FR'])
    MaxQ2 = np.amax(Q_total['FL'])
    MaxQ3 = np.amax(Q_total['FT'])
    MaxQ4 = np.amax(Q_total['FB'])
    MaxQs = np.array([MaxQ1, MaxQ2, MaxQ3, MaxQ4])
    MaxQ_Front = np.amax(MaxQs)
    
    Q_minCalc = MinQ_Middle 
    Q_maxCalc = MaxQ_Front
    Q_min = np.maximum(Absolute_Q_min, Q_minCalc)
    Q_max = np.minimum(Absolute_Q_max, Q_maxCalc)
    Q_bins = int(150*(Q_max - Q_min)/(Q_maxCalc - Q_minCalc))
    

    if str(Config).find('CvB') != -1:
        HR_Q_min = np.amin(Q_total['B'])
        Q_min_HR = np.maximum(HR_Q_min, Absolute_Q_min)
        HR_bins = int(np.sqrt(np.power((HighResMaxX - HighResMinX + 1)/2, 2) + np.power((HighResMaxY - HighResMinY + 1)/2, 2)))

        Q_min = Q_min_HR
        Q_bins = 4*(Q_bins + HR_bins)
    
    return Q_min, Q_max, Q_bins

def TwoDimToOneDim(Key, Q_min, Q_max, Q_bins, QGridPerDetector, generalmask, sectormask, PolCorr_AllDetectors, Unc_PolCorr_AllDetectors, ID, Config, PlotYesNo, AverageQRanges):

    masks = {}
    relevant_detectors = short_detectors
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors
    for dshort in relevant_detectors:
        masks[dshort] = generalmask[dshort]*sectormask[dshort]

    Q_Values = np.linspace(Q_min, Q_max, Q_bins, endpoint=True)
    Q_step = (Q_max - Q_min) / Q_bins
    
    FrontUU = np.zeros_like(Q_Values)
    FrontUU_Unc = np.zeros_like(Q_Values)
    FrontMeanQ = np.zeros_like(Q_Values)
    FrontMeanQUnc = np.zeros_like(Q_Values)
    FrontPixels = np.zeros_like(Q_Values)
    
    MiddleUU = np.zeros_like(Q_Values)
    MiddleUU_Unc = np.zeros_like(Q_Values)
    MiddleMeanQ = np.zeros_like(Q_Values)
    MiddleMeanQUnc = np.zeros_like(Q_Values)
    MiddlePixels = np.zeros_like(Q_Values)

    BackUU = np.zeros_like(Q_Values)
    BackUU_Unc = np.zeros_like(Q_Values)
    BackMeanQ = np.zeros_like(Q_Values)
    BackMeanQUnc = np.zeros_like(Q_Values)
    BackPixels = np.zeros_like(Q_Values)
    
    for dshort in relevant_detectors:
        Q_tot = QGridPerDetector['Q_total'][dshort][:][:]
        Q_unc = np.sqrt(np.power(QGridPerDetector['Q_perp_unc'][dshort][:][:],2) + np.power(QGridPerDetector['Q_parl_unc'][dshort][:][:],2))
        UU = PolCorr_AllDetectors[dshort][:][:]
        UU_Unc = Unc_PolCorr_AllDetectors[dshort][:][:]

        Exp_bins = np.linspace(Q_min, Q_max + Q_step, Q_bins + 1, endpoint=True)
        countsUU, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=UU[masks[dshort] > 0])
        
        UncUU, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=np.power(UU_Unc[masks[dshort] > 0],2))
        
        MeanQSum, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=Q_tot[masks[dshort] > 0])
        MeanQUnc, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=np.power(Q_unc[masks[dshort] > 0],2)) 
        pixels, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=np.ones_like(UU)[masks[dshort] > 0])
        
        carriage_key = dshort[0]
        if carriage_key == 'F':
            FrontUU += countsUU
            FrontUU_Unc += UncUU
            FrontMeanQ += MeanQSum
            FrontMeanQUnc += MeanQUnc
            FrontPixels += pixels
        elif carriage_key == 'M':
            MiddleUU += countsUU
            MiddleUU_Unc += UncUU
            MiddleMeanQ += MeanQSum
            MiddleMeanQUnc += MeanQUnc
            MiddlePixels += pixels
        else:
            BackUU += countsUU
            BackUU_Unc += UncUU
            BackMeanQ += MeanQSum
            BackMeanQUnc += MeanQUnc
            BackPixels += pixels

    CombinedPixels = FrontPixels + MiddlePixels + BackPixels
    nonzero_front_mask = (FrontPixels > 0) #True False map
    nonzero_middle_mask = (MiddlePixels > 0) #True False map
    nonzero_back_mask = (BackPixels > 0) #True False map
    nonzero_combined_mask = (CombinedPixels > 0) #True False map
    
    Q_Front = Q_Values[nonzero_front_mask]
    MeanQ_Front = FrontMeanQ[nonzero_front_mask] / FrontPixels[nonzero_front_mask]
    MeanQUnc_Front = np.sqrt(FrontMeanQUnc[nonzero_front_mask]) / FrontPixels[nonzero_front_mask]
    UUF = FrontUU[nonzero_front_mask] / FrontPixels[nonzero_front_mask]
    
    Q_Middle = Q_Values[nonzero_middle_mask]
    MeanQ_Middle = MiddleMeanQ[nonzero_middle_mask] / MiddlePixels[nonzero_middle_mask]
    MeanQUnc_Middle = np.sqrt(MiddleMeanQUnc[nonzero_middle_mask]) / MiddlePixels[nonzero_middle_mask]
    UUM = MiddleUU[nonzero_middle_mask] / MiddlePixels[nonzero_middle_mask]

    Q_Back = Q_Values[nonzero_back_mask]
    MeanQ_Back = BackMeanQ[nonzero_back_mask] / BackPixels[nonzero_back_mask]
    MeanQUnc_Back = np.sqrt(BackMeanQUnc[nonzero_back_mask]) / BackPixels[nonzero_back_mask]
    UUB = BackUU[nonzero_back_mask] / BackPixels[nonzero_back_mask]

    Sigma_UUF = np.sqrt(FrontUU_Unc[nonzero_front_mask]) / FrontPixels[nonzero_front_mask]
    Sigma_UUM = np.sqrt(MiddleUU_Unc[nonzero_middle_mask]) / MiddlePixels[nonzero_middle_mask]
    Sigma_UUB = np.sqrt(BackUU_Unc[nonzero_back_mask]) / BackPixels[nonzero_back_mask]

    ErrorBarsYesNo = 0
    if PlotYesNo == 1:
        fig = plt.figure()
        if ErrorBarsYesNo == 1:
            ax = plt.axes()
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.errorbar(Q_Front, UUF, yerr=Sigma_UUF, fmt = 'b*', label='Front')
            ax.errorbar(Q_Middle, UUM, yerr=Sigma_UUM, fmt = 'g*', label='Middle')
            if str(Config).find('CvB') != -1:
                ax.errorbar(Q_Back, UUB, yerr=Sigma_UUB, fmt = 'r*', label='HighRes')
        else:
            plt.loglog(Q_Front, UUF, 'b*', label='Front')
            plt.loglog(Q_Middle, UUM, 'g*', label='Middle')
            if str(Config).find('CvB') != -1:
                plt.loglog(Q_Back, UUB, 'r*', label='High Res')
                
        plt.xlabel('Q')
        plt.ylabel('Intensity')
        plt.title('{keyword}_{idnum},{cf}'.format(keyword=Key, idnum=ID, cf = Config))
        plt.legend()
        fig.savefig('{keyword}_{idnum},CF{cf}.png'.format(keyword=Key, idnum=ID, cf = Config))
        plt.show()

    if AverageQRanges == 0:
        '''Remove points overlapping in Q space before joining'''
        for entry in Q_Back:
            if entry in Q_Middle:
                index_position = np.where(Q_Back == entry)
                Q_Back_Temp = np.delete(Q_Back, [index_position])
                Q_Back = Q_Back_Temp
                MeanQ_Back_Temp = np.delete(MeanQ_Back, [index_position])
                MeanQ_Back = MeanQ_Back_Temp
                MeanQUnc_Back_Temp = np.delete(MeanQUnc_Back, [index_position])
                MeanQUnc_Back = MeanQUnc_Back_Temp
                UUB_Temp = np.delete(UUB, [index_position])
                UUB = UUB_Temp
                Sigma_UUB_Temp =  np.delete(Sigma_UUB, [index_position])
                Sigma_UUB = Sigma_UUB_Temp
        for entry in Q_Middle:
            if entry in Q_Front:
                index_position = np.where(Q_Middle == entry)
                Q_Middle_Temp = np.delete(Q_Middle, [index_position])
                Q_Middle = Q_Middle_Temp
                MeanQ_Middle_Temp = np.delete(MeanQ_Middle, [index_position])
                MeanQ_Middle = MeanQ_Middle_Temp
                MeanQUnc_Middle_Temp = np.delete(MeanQUnc_Middle, [index_position])
                MeanQUnc_Middle = MeanQUnc_Middle_Temp
                UUM_Temp = np.delete(UUM, [index_position])
                UUM = UUM_Temp
                Sigma_UUM_Temp =  np.delete(Sigma_UUM, [index_position])
                Sigma_UUM = Sigma_UUM_Temp  
        Q_Common = np.concatenate((Q_Back, Q_Middle, Q_Front), axis=0)
        Q_Mean = np.concatenate((MeanQ_Back, MeanQ_Middle, MeanQ_Front), axis=0)
        Q_Uncertainty = np.concatenate((MeanQUnc_Back, MeanQUnc_Middle, MeanQUnc_Front), axis=0)
        UU = np.concatenate((UUB, UUM, UUF), axis=0)
        SigmaUU = np.concatenate((Sigma_UUB, Sigma_UUM, Sigma_UUF), axis=0)
        Shadow = np.ones_like(Q_Common)  
    else:
        Q_Common = Q_Values[nonzero_combined_mask]
        CombinedMeanQ = BackMeanQ + MiddleMeanQ + FrontMeanQ
        CombinedMeanQUnc = BackMeanQUnc + MiddleMeanQUnc + FrontMeanQUnc
        Q_Mean = CombinedMeanQ[nonzero_combined_mask] / CombinedPixels[nonzero_combined_mask]
        Q_Uncertainty = np.sqrt(CombinedMeanQUnc[nonzero_combined_mask]) / CombinedPixels[nonzero_combined_mask]
        CombinedUU = BackUU + MiddleUU + FrontUU
        UU = CombinedUU[nonzero_combined_mask] / CombinedPixels[nonzero_combined_mask]
        UU_UncC = BackUU_Unc + MiddleUU_Unc + FrontUU_Unc
        SigmaUU = np.sqrt(UU_UncC[nonzero_combined_mask]) / CombinedPixels[nonzero_combined_mask]
        Shadow = np.ones_like(Q_Common)

    Output = {}
    Output['Q'] = Q_Common
    Output['Q_Mean'] = Q_Mean
    Output['I'] = UU
    Output['I_Unc'] = SigmaUU
    Output['Q_Uncertainty'] = Q_Uncertainty
    Output['Shadow'] = Shadow
     
    return Output

def Raw_Data(filenumber):

    RawData_AllDetectors = {}
    Unc_RawData_AllDetectors = {}

    f = get_by_filenumber(filenumber)
    if f is not None:
        for dshort in short_detectors:
            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
            RawData_AllDetectors[dshort] = data
            Unc_RawData_AllDetectors[dshort] = np.sqrt(data)
                    
    return RawData_AllDetectors, Unc_RawData_AllDetectors

def ASCIIlike_Output(Type, ID, Config, Data_AllDetectors, Unc_Data_AllDetectors, QGridPerDetector, GeneralMask):

    relevant_detectors = short_detectors
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors

    if 'NA' not in Data_AllDetectors and 'NA' not in Unc_Data_AllDetectors:

        for dshort in relevant_detectors:

            Mask = np.array(GeneralMask[dshort])
            mini_mask = Mask > 0

            Q_tot = QGridPerDetector['Q_total'][dshort][:][:]
            Q_unc = np.sqrt(np.power(QGridPerDetector['Q_perp_unc'][dshort][:][:],2) + np.power(QGridPerDetector['Q_parl_unc'][dshort][:][:],2))

            QQX = QGridPerDetector['QX'][dshort][:][:]
            QQX = QQX[mini_mask,...]
            QQX = QQX.T
            QXData = QQX.flatten()
            QQY = QGridPerDetector['QY'][dshort][:][:]
            QQY = QQY[mini_mask,...]
            QQY = QQY.T
            QYData = QQY.flatten()
            QQZ = QGridPerDetector['QZ'][dshort][:][:]
            QQZ = QQZ[mini_mask,...]
            QQZ = QQZ.T
            QZData = QQZ.flatten()
            QPP = QGridPerDetector['Q_perp_unc'][dshort][:][:]
            QPP = QPP[mini_mask,...]
            QPP = QPP.T
            QPerpUnc = QPP.flatten()
            QPR = QGridPerDetector['Q_parl_unc'][dshort][:][:]
            QPR = QPR[mini_mask,...]
            QPR = QPR.T
            QParlUnc = QPR.flatten()
            Shadow = np.ones_like(Q_tot)
            Shadow = Shadow[mini_mask,...]
            Shadow = Shadow.T
            ShadowHolder = Shadow.flatten()

            Intensity = Data_AllDetectors[dshort]
            Intensity = Intensity[mini_mask,...]
            Intensity = Intensity.T
            Int = Intensity.flatten()
            Intensity = Intensity.flatten()
            IntensityUnc = Unc_Data_AllDetectors[dshort]
            IntensityUnc = IntensityUnc[mini_mask,...]
            IntensityUnc = IntensityUnc.T
            DeltaInt = IntensityUnc.flatten()
            IntensityUnc = IntensityUnc.flatten()
            if YesNo_2DFilesPerDetector > 0:
                print('Outputting Unpol data into ASCII-like format for {det}, GroupID = {idnum} '.format(det=dshort, idnum=ID))
                ASCII_like = np.array([QXData, QYData, Int, DeltaInt, QZData, QParlUnc, QPerpUnc, ShadowHolder])
                ASCII_like = ASCII_like.T
                np.savetxt('{TP}Scatt_{Samp}_{CF}_{det}.DAT'.format(TP=Type, Samp=ID, CF=Config, det=dshort), ASCII_like, delimiter = ' ', comments = ' ', header = 'ASCII data created Mon, Jan 13, 2020 2:39:54 PM')
           

            if dshort == relevant_detectors[0]:
                Int_Combined = Intensity
                DeltaInt_Combined = IntensityUnc
                QXData_Combined = QXData
                QYData_Combined = QYData
                QZData_Combined = QZData
                QPP_Combined = QPP
                QPerpUnc_Combined = QPerpUnc
                QPR_Combined = QPR
                QParlUnc_Combined = QParlUnc
                Shadow_Combined = ShadowHolder
            else:
                Int_Combined = np.concatenate((Int_Combined, Intensity), axis=0)
                DeltaInt_Combined = np.concatenate((DeltaInt_Combined, IntensityUnc), axis=0)
                QXData_Combined = np.concatenate((QXData_Combined, QXData), axis=0)
                QYData_Combined = np.concatenate((QYData_Combined, QYData), axis=0)
                QZData_Combined = np.concatenate((QZData_Combined, QZData), axis=0)
                QPP_Combined = np.concatenate((QPP_Combined, QPP), axis=0)
                QPerpUnc_Combined = np.concatenate((QPerpUnc_Combined, QPerpUnc), axis=0)
                QPR_Combined = np.concatenate((QPR_Combined, QPR), axis=0)
                QParlUnc_Combined = np.concatenate((QParlUnc_Combined, QParlUnc), axis=0)
                Shadow_Combined = np.concatenate((Shadow_Combined, ShadowHolder), axis=0)

        print('Outputting {TP} 2D data, {idnum}, {CF} '.format(TP=Type, idnum=ID, CF=Config))        
        ASCII_Combined = np.array([QXData_Combined, QYData_Combined, Int_Combined, DeltaInt_Combined, QZData_Combined, QParlUnc_Combined, QPerpUnc_Combined, Shadow_Combined])
        ASCII_Combined = ASCII_Combined.T
        np.savetxt(save_path + 'Dim2Scatt_{Samp}_{CF}_{TP}.DAT'.format(Samp=ID, CF=Config, TP=Type,), ASCII_Combined, delimiter = ' ', comments = ' ', header = 'ASCII data created Mon, Jan 13, 2020 2:39:54 PM')

    return

def SaveTextData(Type, Slice, Sample, Config, DataMatrix):

    Q = DataMatrix['Q']
    Int = DataMatrix['I']
    IntUnc = DataMatrix['I_Unc']
    Q_mean = DataMatrix['Q_Mean']
    Q_Unc = DataMatrix['Q_Uncertainty']
    Shadow = np.ones_like(Q)
    text_output = np.array([Q, Int, IntUnc, Q_Unc, Q_mean, Shadow])
    #text_output = np.array([Q, Int, IntUnc, Q_mean, Q_Unc, Shadow])
    text_output = text_output.T
    np.savetxt(save_path + 'SixCol_{samp},{cf}_{key}{cut}.txt'.format(samp=Sample, cf = Config, key = Type, cut = Slice), text_output, delimiter = ' ', comments = ' ', header= 'Q, I, DelI, Q_Unc, Q_mean, Shadow', fmt='%1.4e')
  
    return


def SaveTextDataFourCrossSections(Type, Slice, Sample, Config, UUMatrix, DUMatrix, DDMatrix, UDMatrix):

    Q = UUMatrix['Q']
    UU = UUMatrix['I']
    UU_Unc = UUMatrix['I_Unc']
    DU = DUMatrix['I']
    DU_Unc = DUMatrix['I_Unc']
    DD = DDMatrix['I']
    DD_Unc = DDMatrix['I_Unc']
    UD = UDMatrix['I']
    UD_Unc = UDMatrix['I_Unc']
    Q_mean = UUMatrix['Q_Mean']
    Q_Unc = UUMatrix['Q_Uncertainty']
    Shadow = np.ones_like(Q)
    text_output = np.array([Q, UU, UU_Unc, DU, DU_Unc, DD, DD_Unc, UD, UD_Unc, Q_Unc, Q_mean, Shadow])
    text_output = text_output.T
    np.savetxt(save_path + 'SliceFullPol_{samp},{cf}_{key}{cut}.txt'.format(samp=Sample, cf = Config, key = Type, cut = Slice), text_output,
               delimiter = ' ', comments = ' ', header= 'Q, UU, DelUU, DU, DelDU, DD, DelDD, UD, DelUD, Q_Unc, Q_mean, Shadow', fmt='%1.4e')
  
    return

def SaveTextDataFourCombinedCrossSections(Type, Slice, Sub, Sample, Config, Matrix):

    Q = Matrix['Q']
    UU = Matrix['UU']
    UU_Unc = Matrix['UU_Unc']
    DU = Matrix['DU']
    DU_Unc = Matrix['DU_Unc']
    DD = Matrix['DD']
    DD_Unc = Matrix['DD_Unc']
    UD = Matrix['UD']
    UD_Unc = Matrix['UD_Unc']
    Q_mean = Matrix['Q_Mean']
    Q_Unc = Matrix['Q_Unc']
    Shadow = Matrix['Shadow']
    text_output = np.array([Q, UU, UU_Unc, DU, DU_Unc, DD, DD_Unc, UD, UD_Unc, Q_Unc, Q_mean, Shadow])
    text_output = text_output.T
    np.savetxt(save_path + 'SliceFullPol_{samp},{cf}_{key}{cut}{sub}.txt'.format(samp=Sample, cf = Config, key = Type, cut = Slice, sub = Sub), text_output,
               delimiter = ' ', comments = ' ', header= 'Q, UU, DelUU, DU, DelDU, DD, DelDD, UD, DelUD, Q_Unc, Q_mean, Shadow', fmt='%1.4e')
  
    return

def PlotFourCrossSections(Type, Slice, Sample, Config, UU, DU, DD, UD):

    fig = plt.figure()
    ax = plt.axes()
    ax.set_xscale("log")
    ax.set_yscale("log")
    if YesNoSetPlotYRange > 0:
        ax.set_ylim(bottom = PlotYmin, top = PlotYmax)
    if YesNoSetPlotXRange > 0:
        ax.set_xlim(left = PlotXmin, right = PlotXmax)
    ax.errorbar(UU['Q'], UU['I'], yerr=UU['I_Unc'], fmt = 'b*', label='UU')
    ax.errorbar(DU['Q'], DU['I'], yerr=DU['I_Unc'], fmt = 'g*', label='DU')
    ax.errorbar(DD['Q'], DD['I'], yerr=DD['I_Unc'], fmt = 'r*', label='DD')
    ax.errorbar(UD['Q'], UD['I'], yerr=UD['I_Unc'], fmt = 'm*', label='UD')
    plt.xlabel('Q (inverse angstroms)')
    plt.ylabel('Intensity')
    plt.title('{slice_type}_{idnum},{cf}'.format(slice_type = Slice, idnum=Sample, cf = Config))
    plt.legend()
    fig.savefig(save_path + 'SliceFullPol_{samp},{cf}_{corr}{slice_type}.png'.format(samp=Sample, cf = Config, corr = Type, slice_type = Slice))
    if YesNoShowPlots > 0:
        plt.pause(2)
    plt.close()

    return

def PlotFourCombinedCrossSections(Type, Slice, Sub, Sample, Config, Matrix):

    fig = plt.figure()
    ax = plt.axes()
    ax.set_xscale("log")
    ax.set_yscale("log")
    if YesNoSetPlotYRange > 0:
        ax.set_ylim(bottom = PlotYmin, top = PlotYmax)
    if YesNoSetPlotXRange > 0:
        ax.set_xlim(left = PlotXmin, right = PlotXmax)
    ax.errorbar(Matrix['Q'], Matrix['UU'], yerr=Matrix['UU_Unc'], fmt = 'b*', label='UU')
    ax.errorbar(Matrix['Q'], Matrix['DU'], yerr=Matrix['DU_Unc'], fmt = 'g*', label='DU')
    ax.errorbar(Matrix['Q'], Matrix['DD'], yerr=Matrix['DD_Unc'], fmt = 'r*', label='DD')
    ax.errorbar(Matrix['Q'], Matrix['UD'], yerr=Matrix['UD_Unc'], fmt = 'm*', label='UD')
    plt.xlabel('Q (inverse angstroms)')
    plt.ylabel('Intensity')
    plt.title('{slice_type}_{idnum},{cf}'.format(slice_type = Slice, idnum=Sample, cf = Config))
    plt.legend()
    fig.savefig(save_path + 'SliceFullPol_{samp},{cf}_{corr}{slice_type}{sub}.png'.format(samp=Sample, cf = Config, corr = Type, slice_type = Slice, sub = Sub))
    if YesNoShowPlots > 0:
        plt.pause(2)
    plt.close()

    return

def vSANS_FullPolSlices(PolCorrDegree, Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, PolCorrUU, PolCorrUU_Unc, PolCorrDU, PolCorrDU_Unc, PolCorrDD, PolCorrDD_Unc, PolCorrUD, PolCorrUD_Unc):

    relevant_detectors = short_detectors
    AverageQRanges = 1
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors
        AverageQRanges = 0

    Corr = "PolCorr"
    if PolCorrDegree >= 2:
        Corr = "PolCorr"
    elif PolCorrDegree >= 1:
        Corr = "He3Corr"
    else:
        Corr = "NotCorr"

    PlotYesNo = 0
    BothSides = 1
    HorzMask = SectorMask_AllDetectors(InPlaneAngleMap, 0, SectorCutAngles, BothSides)
    VertMask = SectorMask_AllDetectors(InPlaneAngleMap, 90, SectorCutAngles, BothSides)
    CircMask = SectorMask_AllDetectors(InPlaneAngleMap, 0, 180, BothSides)
    DiagMaskA = SectorMask_AllDetectors(InPlaneAngleMap, 45, SectorCutAngles, BothSides)
    DiagMaskB = SectorMask_AllDetectors(InPlaneAngleMap, -45, SectorCutAngles, BothSides)
    DiagMask = {}
    for dshort in relevant_detectors:
        DiagMask[dshort] = DiagMaskA[dshort] + DiagMaskB[dshort]

    ReturnSlices = {}
    
    for slices in Slices:
        if slices == "Circ":
            slice_key = "CircAve"
            local_mask = CircMask
        elif slices == "Vert":
            slice_key = "Vert"+str(SectorCutAngles)
            local_mask = VertMask
        elif slices == "Horz":
            slice_key = "Horz"+str(SectorCutAngles)
            local_mask = HorzMask
        elif slices == "Diag":
            slice_key = "Diag"+str(SectorCutAngles)
            local_mask = DiagMask

        UU = TwoDimToOneDim(slice_key, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, local_mask, PolCorrUU, PolCorrUU_Unc, Sample, Config, PlotYesNo, AverageQRanges)
        DU = TwoDimToOneDim(slice_key, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, local_mask, PolCorrDU, PolCorrDU_Unc, Sample, Config, PlotYesNo, AverageQRanges)
        DD = TwoDimToOneDim(slice_key, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, local_mask, PolCorrDD, PolCorrDD_Unc, Sample, Config, PlotYesNo, AverageQRanges)
        UD = TwoDimToOneDim(slice_key, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, local_mask, PolCorrUD, PolCorrUD_Unc, Sample, Config, PlotYesNo, AverageQRanges)

        #SaveTextDataFourCrossSections('{corr}'.format(corr = Corr), slice_key, Sample, Config, UU, DU, DD, UD)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''

        #PlotFourCrossSections('{corr}'.format(corr = Corr), slice_key, Sample, Config, UU, DU, DD, UD)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''

        ReturnSlices[slice_key] = {'PolType' : Corr, 'UU' : UU, 'DU' : DU, 'DD' : DD, 'UD' : UD}

    return ReturnSlices

def vSANS_HalfPolSlices(PolType, Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, U, U_Unc, D, D_Unc):

    relevant_detectors = short_detectors
    AverageQRanges = 1
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors
        AverageQRanges = 0

    PlotYesNo = 0
    BothSides = 1
    HorzMask = SectorMask_AllDetectors(InPlaneAngleMap, 0, SectorCutAngles, BothSides)
    VertMask = SectorMask_AllDetectors(InPlaneAngleMap, 90, SectorCutAngles, BothSides)
    CircMask = SectorMask_AllDetectors(InPlaneAngleMap, 0, 180, BothSides)
    DiagMaskA = SectorMask_AllDetectors(InPlaneAngleMap, 45, SectorCutAngles, BothSides)
    DiagMaskB = SectorMask_AllDetectors(InPlaneAngleMap, -45, SectorCutAngles, BothSides)
    DiagMask = {}
    for dshort in relevant_detectors:
        DiagMask[dshort] = DiagMaskA[dshort] + DiagMaskB[dshort]

    ReturnSlices = {}
    
    for slices in Slices:
        if slices == "Circ":
            slice_key = "CircAve"
            local_mask = CircMask
        elif slices == "Vert":
            slice_key = "Vert"+str(SectorCutAngles)
            local_mask = VertMask
        elif slices == "Horz":
            slice_key = "Horz"+str(SectorCutAngles)
            local_mask = HorzMask
        elif slices == "Diag":
            slice_key = "Diag"+str(SectorCutAngles)
            local_mask = DiagMask

        UCut = TwoDimToOneDim(slice_key, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, local_mask, U, U_Unc, Sample, Config, PlotYesNo, AverageQRanges)
        DCut = TwoDimToOneDim(slice_key, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, local_mask, D, D_Unc, Sample, Config, PlotYesNo, AverageQRanges)

        ReturnSlices[slice_key] = {'PolType' : PolType, 'U' : UCut, 'D' : DCut}

    return ReturnSlices

def vSANS_UnpolSlices(PolType, Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, Unpol, Unpol_Unc):

    relevant_detectors = short_detectors
    AverageQRanges = 1
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors
        AverageQRanges = 0

    PlotYesNo = 0
    BothSides = 1
    HorzMask = SectorMask_AllDetectors(InPlaneAngleMap, 0, SectorCutAngles, BothSides)
    VertMask = SectorMask_AllDetectors(InPlaneAngleMap, 90, SectorCutAngles, BothSides)
    CircMask = SectorMask_AllDetectors(InPlaneAngleMap, 0, 180, BothSides)
    DiagMaskA = SectorMask_AllDetectors(InPlaneAngleMap, 45, SectorCutAngles, BothSides)
    DiagMaskB = SectorMask_AllDetectors(InPlaneAngleMap, -45, SectorCutAngles, BothSides)
    DiagMask = {}
    for dshort in relevant_detectors:
        DiagMask[dshort] = DiagMaskA[dshort] + DiagMaskB[dshort]

    ReturnSlices = {}
    
    for slices in Slices:
        if slices == "Circ":
            slice_key = "CircAve"
            local_mask = CircMask
        elif slices == "Vert":
            slice_key = "Vert"+str(SectorCutAngles)
            local_mask = VertMask
        elif slices == "Horz":
            slice_key = "Horz"+str(SectorCutAngles)
            local_mask = HorzMask
        elif slices == "Diag":
            slice_key = "Diag"+str(SectorCutAngles)
            local_mask = DiagMask

        UnpolCut = TwoDimToOneDim(slice_key, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, local_mask, Unpol, Unpol_Unc, Sample, Config, PlotYesNo, AverageQRanges)
        
        ReturnSlices[slice_key] = {'PolType' : PolType, 'Unpol' : UnpolCut}

    return ReturnSlices

def MatchQ_PADataSets(A, B, Type):
    '''if Type = 0 Unpol, if Type = 1 Half Pol, if Type = 2 FullPol'''

    Horz_Data = A
    Vert_Data = B
    
    for entry in Horz_Data['Q']:
        if entry not in Vert_Data['Q']:
            result = np.where(Horz_Data['Q'] == entry)
            Horz_Data['Q'] = np.delete(Horz_Data['Q'], result)
            Horz_Data['Q_Mean'] = np.delete(Horz_Data['Q_Mean'], result)
            Horz_Data['Q_Unc'] = np.delete(Horz_Data['Q_Unc'], result)
            Horz_Data['Shadow'] = np.delete(Horz_Data['Shadow'], result)
            if Type == 0:
                Horz_Data['Unpol'] = np.delete(Horz_Data['Unpol'], result)
                Horz_Data['Unpol_Unc'] = np.delete(Horz_Data['Unpol_Unc'], result)
            if Type == 1:
                Horz_Data['U'] = np.delete(Horz_Data['U'], result)
                Horz_Data['U_Unc'] = np.delete(Horz_Data['U_Unc'], result)
                Horz_Data['D'] = np.delete(Horz_Data['D'], result)
                Horz_Data['D_Unc'] = np.delete(Horz_Data['D_Unc'], result)
            if Type == 2:
                Horz_Data['UU'] = np.delete(Horz_Data['UU'], result)
                Horz_Data['UU_Unc'] = np.delete(Horz_Data['UU_Unc'], result)
                Horz_Data['DU'] = np.delete(Horz_Data['DU'], result)
                Horz_Data['DU_Unc'] = np.delete(Horz_Data['DU_Unc'], result)
                Horz_Data['DD'] = np.delete(Horz_Data['DD'], result)
                Horz_Data['DD_Unc'] = np.delete(Horz_Data['DD_Unc'], result)
                Horz_Data['UD'] = np.delete(Horz_Data['UD'], result)
                Horz_Data['UD_Unc'] = np.delete(Horz_Data['UD_Unc'], result)
    for entry in Vert_Data['Q']:
        if entry not in Horz_Data['Q']:
            result = np.where(Vert_Data['Q'] == entry)
            Vert_Data['Q'] = np.delete(Vert_Data['Q'], result)
            Vert_Data['Q_Mean'] = np.delete(Vert_Data['Q_Mean'], result)
            Vert_Data['Q_Unc'] = np.delete(Vert_Data['Q_Unc'], result)
            Vert_Data['Shadow'] = np.delete(Vert_Data['Shadow'], result)
            if Type == 0:
                Vert_Data['Unpol'] = np.delete(Vert_Data['Unpol'], result)
                Vert_Data['Unpol_Unc'] = np.delete(Vert_Data['Unpol_Unc'], result)
            if Type == 1:
                Vert_Data['U'] = np.delete(Vert_Data['U'], result)
                Vert_Data['U_Unc'] = np.delete(Vert_Data['U_Unc'], result)
                Vert_Data['D'] = np.delete(Vert_Data['D'], result)
                Vert_Data['D_Unc'] = np.delete(Vert_Data['D_Unc'], result)
            if Type == 2:
                Vert_Data['UU'] = np.delete(Vert_Data['UU'], result)
                Vert_Data['UU_Unc'] = np.delete(Vert_Data['UU_Unc'], result)
                Vert_Data['DU'] = np.delete(Vert_Data['DU'], result)
                Vert_Data['DU_Unc'] = np.delete(Vert_Data['DU_Unc'], result)
                Vert_Data['DD'] = np.delete(Vert_Data['DD'], result)
                Vert_Data['DD_Unc'] = np.delete(Vert_Data['DD_Unc'], result)
                Vert_Data['UD'] = np.delete(Vert_Data['UD'], result)
                Vert_Data['UD_Unc'] = np.delete(Vert_Data['UD_Unc'], result)

    return Horz_Data, Vert_Data

def Subtract_PADataSets(A, B, Type):
    '''if Type = 0 Unpol, if Type = 1 Half Pol, if Type = 2 FullPol'''

    C = {}
    C['Q'] = A['Q']
    C['Q_Mean'] = A['Q_Mean']
    C['Q_Unc'] = A['Q_Unc']
    C['Shadow'] = A['Shadow']
    if Type == 0:
        C['Unpol'] = A['Unpol'] - B['Unpol']
        C['Unpol_Unc'] = np.sqrt(np.power(A['Unpol_Unc'],2) + np.power(B['Unpol_Unc'],2))
    if Type == 1:
        C['U'] = A['U'] - B['U']
        C['U_Unc'] = np.sqrt(np.power(A['U_Unc'],2) + np.power(B['U_Unc'],2))
        C['D'] = A['D'] - B['D']
        C['D_Unc'] = np.sqrt(np.power(A['D_Unc'],2) + np.power(B['D_Unc'],2))
    if Type == 2:
        C['UU'] = A['UU'] - B['UU']
        C['UU_Unc'] = np.sqrt(np.power(A['UU_Unc'],2) + np.power(B['UU_Unc'],2))
        C['DD'] = A['DD'] - B['DD']
        C['DD_Unc'] = np.sqrt(np.power(A['DD_Unc'],2) + np.power(B['DD_Unc'],2))
        C['UD'] = A['UD'] - B['UD']
        C['UD_Unc'] = np.sqrt(np.power(A['UD_Unc'],2) + np.power(B['UD_Unc'],2))
        C['DU'] = A['DU'] - B['DU']
        C['DU_Unc'] = np.sqrt(np.power(A['DU_Unc'],2) + np.power(B['DU_Unc'],2))
    
    return C

def vSANS_ProcessFullPolSlices(PolSampleSlices, Sample, PolEmptySlices):
    '''Note uses AutoSubtractEmpty  and UseMTCirc from UserInput.py'''

    Sub = ""

    Vert_Data = {}
    Horz_Data = {}
    Diag_Data = {}
    Circ_Data = {}
    MT = {}
    MTCirc = {}
    HaveMTCirc = 0
    HaveVertData = 0
    HaveHorzData = 0
    HaveDiagData = 0
    HaveCircData = 0

    if "Circ" in Slices:
        slice_details = "CircAve"
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveCircData = 1
        Circ_Data['Q'] = PolSampleSlices[Sample][slice_details]['UU']['Q']
        Circ_Data['UU'] = PolSampleSlices[Sample][slice_details]['UU']['I']
        Circ_Data['UU_Unc'] = PolSampleSlices[Sample][slice_details]['UU']['I_Unc']
        Circ_Data['DU'] = PolSampleSlices[Sample][slice_details]['DU']['I']
        Circ_Data['DU_Unc'] = PolSampleSlices[Sample][slice_details]['DU']['I_Unc']
        Circ_Data['DD'] = PolSampleSlices[Sample][slice_details]['DD']['I']
        Circ_Data['DD_Unc'] = PolSampleSlices[Sample][slice_details]['DD']['I_Unc']
        Circ_Data['UD'] = PolSampleSlices[Sample][slice_details]['UD']['I']
        Circ_Data['UD_Unc'] = PolSampleSlices[Sample][slice_details]['UD']['I_Unc']
        Circ_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['UU']['Q_Mean']
        Circ_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['UU']['Q_Uncertainty']
        Circ_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['UU']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                HaveMTCirc = 1
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['UU']['Q']
                MT['UU'] = PolEmptySlices['Empty'][slice_details]['UU']['I']
                MT['UU_Unc'] = PolEmptySlices['Empty'][slice_details]['UU']['I_Unc']
                MT['DU'] = PolEmptySlices['Empty'][slice_details]['DU']['I']
                MT['DU_Unc'] = PolEmptySlices['Empty'][slice_details]['DU']['I_Unc']
                MT['DD'] = PolEmptySlices['Empty'][slice_details]['DD']['I']
                MT['DD_Unc'] = PolEmptySlices['Empty'][slice_details]['DD']['I_Unc']
                MT['UD'] = PolEmptySlices['Empty'][slice_details]['UD']['I']
                MT['UD_Unc'] = PolEmptySlices['Empty'][slice_details]['UD']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['UU']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['UU']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['UU']['Shadow']
                MTCirc = MT

                CircMatch, MTMatch = MatchQ_PADataSets(Circ_Data, MT, 2)
                Circ_Data = Subtract_PADataSets(CircMatch, MTMatch, 2)

        SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Circ_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Circ_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''
        Circ_Sum = (Circ_Data['UU'] + Circ_Data['DU'] + Circ_Data['DD'] + Circ_Data['UD'])/2.0
        Circ_Sum_Unc = (np.sqrt(np.power(Circ_Data['UU_Unc'],2) + np.power(Circ_Data['UD_Unc'],2) + np.power(Circ_Data['DD_Unc'],2) + np.power(Circ_Data['DU_Unc'],2)))/2.0

    if "Horz" in Slices:
        slice_details = "Horz"+str(SectorCutAngles)
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveHorzData = 1
        Horz_Data['Q'] = PolSampleSlices[Sample][slice_details]['UU']['Q']
        Horz_Data['UU'] = PolSampleSlices[Sample][slice_details]['UU']['I']
        Horz_Data['UU_Unc'] = PolSampleSlices[Sample][slice_details]['UU']['I_Unc']
        Horz_Data['DU'] = PolSampleSlices[Sample][slice_details]['DU']['I']
        Horz_Data['DU_Unc'] = PolSampleSlices[Sample][slice_details]['DU']['I_Unc']
        Horz_Data['DD'] = PolSampleSlices[Sample][slice_details]['DD']['I']
        Horz_Data['DD_Unc'] = PolSampleSlices[Sample][slice_details]['DD']['I_Unc']
        Horz_Data['UD'] = PolSampleSlices[Sample][slice_details]['UD']['I']
        Horz_Data['UD_Unc'] = PolSampleSlices[Sample][slice_details]['UD']['I_Unc']
        Horz_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['UU']['Q_Mean']
        Horz_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['UU']['Q_Uncertainty']
        Horz_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['UU']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['UU']['Q']
                MT['UU'] = PolEmptySlices['Empty'][slice_details]['UU']['I']
                MT['UU_Unc'] = PolEmptySlices['Empty'][slice_details]['UU']['I_Unc']
                MT['DU'] = PolEmptySlices['Empty'][slice_details]['DU']['I']
                MT['DU_Unc'] = PolEmptySlices['Empty'][slice_details]['DU']['I_Unc']
                MT['DD'] = PolEmptySlices['Empty'][slice_details]['DD']['I']
                MT['DD_Unc'] = PolEmptySlices['Empty'][slice_details]['DD']['I_Unc']
                MT['UD'] = PolEmptySlices['Empty'][slice_details]['UD']['I']
                MT['UD_Unc'] = PolEmptySlices['Empty'][slice_details]['UD']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['UU']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['UU']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['UU']['Shadow']

                if UseMTCirc == 1 and HaveMTCirc == 1:
                    HorzMatch, MTMatch = MatchQ_PADataSets(Horz_Data, MTCirc, 2)
                else:
                    HorzMatch, MTMatch = MatchQ_PADataSets(Horz_Data, MT, 2)
                Horz_Data = Subtract_PADataSets(HorzMatch, MTMatch, 2)

        SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Horz_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Horz_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''

    if "Vert" in Slices:
        slice_details = "Vert"+str(SectorCutAngles)
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveVertData = 1
        Vert_Data['Q'] = PolSampleSlices[Sample][slice_details]['UU']['Q']
        Vert_Data['UU'] = PolSampleSlices[Sample][slice_details]['UU']['I']
        Vert_Data['UU_Unc'] = PolSampleSlices[Sample][slice_details]['UU']['I_Unc']
        Vert_Data['DU'] = PolSampleSlices[Sample][slice_details]['DU']['I']
        Vert_Data['DU_Unc'] = PolSampleSlices[Sample][slice_details]['DU']['I_Unc']
        Vert_Data['DD'] = PolSampleSlices[Sample][slice_details]['DD']['I']
        Vert_Data['DD_Unc'] = PolSampleSlices[Sample][slice_details]['DD']['I_Unc']
        Vert_Data['UD'] = PolSampleSlices[Sample][slice_details]['UD']['I']
        Vert_Data['UD_Unc'] = PolSampleSlices[Sample][slice_details]['UD']['I_Unc']
        Vert_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['UU']['Q_Mean']
        Vert_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['UU']['Q_Uncertainty']
        Vert_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['UU']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['UU']['Q']
                MT['UU'] = PolEmptySlices['Empty'][slice_details]['UU']['I']
                MT['UU_Unc'] = PolEmptySlices['Empty'][slice_details]['UU']['I_Unc']
                MT['DU'] = PolEmptySlices['Empty'][slice_details]['DU']['I']
                MT['DU_Unc'] = PolEmptySlices['Empty'][slice_details]['DU']['I_Unc']
                MT['DD'] = PolEmptySlices['Empty'][slice_details]['DD']['I']
                MT['DD_Unc'] = PolEmptySlices['Empty'][slice_details]['DD']['I_Unc']
                MT['UD'] = PolEmptySlices['Empty'][slice_details]['UD']['I']
                MT['UD_Unc'] = PolEmptySlices['Empty'][slice_details]['UD']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['UU']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['UU']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['UU']['Shadow']

                if UseMTCirc == 1 and HaveMTCirc == 1:
                    VertMatch, MTMatch = MatchQ_PADataSets(Vert_Data, MTCirc, 2)
                else:
                    VertMatch, MTMatch = MatchQ_PADataSets(Vert_Data, MT, 2)
                Vert_Data = Subtract_PADataSets(VertMatch, MTMatch, 2)

        SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Vert_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Vert_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''

    if "Diag" in Slices:
        slice_details = "Diag"+str(SectorCutAngles)
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveDiagData = 1
        Diag_Data['Q'] = PolSampleSlices[Sample][slice_details]['UU']['Q']
        Diag_Data['UU'] = PolSampleSlices[Sample][slice_details]['UU']['I']
        Diag_Data['UU_Unc'] = PolSampleSlices[Sample][slice_details]['UU']['I_Unc']
        Diag_Data['DU'] = PolSampleSlices[Sample][slice_details]['DU']['I']
        Diag_Data['DU_Unc'] = PolSampleSlices[Sample][slice_details]['DU']['I_Unc']
        Diag_Data['DD'] = PolSampleSlices[Sample][slice_details]['DD']['I']
        Diag_Data['DD_Unc'] = PolSampleSlices[Sample][slice_details]['DD']['I_Unc']
        Diag_Data['UD'] = PolSampleSlices[Sample][slice_details]['UD']['I']
        Diag_Data['UD_Unc'] = PolSampleSlices[Sample][slice_details]['UD']['I_Unc']
        Diag_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['UU']['Q_Mean']
        Diag_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['UU']['Q_Uncertainty']
        Diag_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['UU']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['UU']['Q']
                MT['UU'] = PolEmptySlices['Empty'][slice_details]['UU']['I']
                MT['UU_Unc'] = PolEmptySlices['Empty'][slice_details]['UU']['I_Unc']
                MT['DU'] = PolEmptySlices['Empty'][slice_details]['DU']['I']
                MT['DU_Unc'] = PolEmptySlices['Empty'][slice_details]['DU']['I_Unc']
                MT['DD'] = PolEmptySlices['Empty'][slice_details]['DD']['I']
                MT['DD_Unc'] = PolEmptySlices['Empty'][slice_details]['DD']['I_Unc']
                MT['UD'] = PolEmptySlices['Empty'][slice_details]['UD']['I']
                MT['UD_Unc'] = PolEmptySlices['Empty'][slice_details]['UD']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['UU']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['UU']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['UU']['Shadow']

                if UseMTCirc == 1 and HaveMTCirc == 1:
                    DiagMatch, MTMatch = MatchQ_PADataSets(Diag_Data, MTCirc, 2)
                else:
                    DiagMatch, MTMatch = MatchQ_PADataSets(Diag_Data, MT, 2)
                Diag_Data = Subtract_PADataSets(DiagMatch, MTMatch, 2)

        SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Diag_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Diag_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''

    if HaveHorzData == 1 and HaveVertData == 1:

        HorzMatch, VertMatch = MatchQ_PADataSets(Horz_Data, Vert_Data, 2)
        for entry in Horz_Data:
            Horz_Data[entry] = HorzMatch[entry]
        for entry in Vert_Data:
            Vert_Data[entry] = VertMatch[entry]
              
        HorzAndVert_Data = {}
        HorzAndVert_Data['Q'] = Horz_Data['Q']
        HorzAndVert_Data['DU'] = Horz_Data['DU'] + Vert_Data['DU']
        HorzAndVert_Data['UD'] = Horz_Data['UD'] + Vert_Data['UD']
        HorzAndVert_Data['DU_Unc'] = np.sqrt(np.power(Horz_Data['DU_Unc'],2) + np.power(Vert_Data['DU_Unc'],2))
        HorzAndVert_Data['UD_Unc'] = np.sqrt(np.power(Horz_Data['UD_Unc'],2) + np.power(Vert_Data['UD_Unc'],2))

        Struc = (Horz_Data['DD'] + Horz_Data['UU'])/2.0
        Struc_Unc = np.sqrt(np.power(Horz_Data['DD_Unc'],2) + np.power(Horz_Data['UU_Unc'],2))/2.0

        M_Perp = (Horz_Data['DU'] + Horz_Data['UD'] + Vert_Data['DU'] + Vert_Data['UD'])/2.0
        M_Perp_Unc = (np.sqrt(np.power(Horz_Data['DU_Unc'],2) + np.power(Horz_Data['UD_Unc'],2) + np.power(Vert_Data['DU_Unc'],2) + np.power(Vert_Data['UD_Unc'],2)))/2.0

        Diff = Vert_Data['DD'] - Vert_Data['UU']
        Diff_Unc = np.sqrt(np.power(Vert_Data['DD_Unc'],2) + np.power(Vert_Data['UU_Unc'],2))
        Num = np.power((Diff),2)
        Num_Unc = np.sqrt(2.0)*Diff*Diff_Unc
        Denom = (4.0*(Horz_Data['DD'] + Horz_Data['UU']))
        Denom_Unc = np.sqrt(np.power(Horz_Data['DD_Unc'],2) + np.power(Horz_Data['UU_Unc'],2))
        M_Parl_NSF = (Num / Denom)/2.0
        M_Parl_NSF_Unc = (M_Parl_NSF * np.sqrt( np.power(Num_Unc,2)/np.power(Num,2) + np.power(Denom_Unc,2)/np.power(Denom,2)))

        if HaveDiagData == 1:
            DiagMatch, HorzAndVertMatch = MatchQ_PADataSets(Diag_Data, HorzAndVert_Data, 2)
            for entry in Diag_Data:
                Diag_Data[entry] = DiagMatch[entry]
            for entry in HorzAndVert_Data:
                HorzAndVert_Data[entry] = HorzAndVertMatch[entry]

            AngleA = (45 - SectorCutAngles)*3.141593/180.0
            AngleB = (45 + SectorCutAngles)*3.141593/180.0
            Factor = (AngleB - AngleA)/4.0 + (np.sin(4.0*AngleA) - np.sin(4.0*AngleB))/32.0
            M_Parl_SF =(2.0*(Diag_Data['UD'] + Diag_Data['DU']) - (4.0*Factor/6)*(HorzAndVert_Data['UD'] + HorzAndVert_Data['DU']))/2.0
            M_Parl_SF_Unc = (np.sqrt(np.power(HorzAndVert_Data['DU_Unc'],2) + np.power(HorzAndVert_Data['UD_Unc'],2) + np.power(Diag_Data['DU_Unc'],2) + np.power(Diag_Data['UD_Unc'],2)))/2.0

        Width = str(SectorCutAngles) + "Deg"
        fig = plt.figure()
        ax = plt.axes()
        ax.set_xscale("log")
        ax.set_yscale("log")
        if YesNoSetPlotYRange > 0:
            ax.set_ylim(bottom = PlotYmin, top = PlotYmax)
        if YesNoSetPlotXRange > 0:
            ax.set_xlim(left = PlotXmin, right = PlotXmax)
        ax.errorbar(Horz_Data['Q'], M_Perp, yerr=M_Perp_Unc, fmt = 'b*', label='M_Perp (spin-flip)')
        ax.errorbar(Horz_Data['Q'], M_Parl_NSF, yerr=M_Parl_NSF_Unc, fmt = 'g*', label='M_Parl (non spin-flip)')
        if HaveDiagData == 1:
            ax.errorbar(Diag_Data['Q'], M_Parl_SF, yerr=M_Parl_SF_Unc, fmt = 'm*', label='M_Parl (spin-flip)')
        ax.errorbar(Horz_Data['Q'], Struc, yerr=Struc_Unc, fmt = 'r*', label='Structural (non spin-flip)')
        plt.xlabel('Q (inverse angstroms)')
        plt.ylabel('Intensity')
        plt.title('Magnetic and Structural Scattering of {samp}'.format(samp=Sample))
        plt.legend()
        fig.savefig(save_path + 'ResultsFullPol_{samp},{cf}_{key}{width}{sub}.png'.format(samp=Sample, cf = Config,  key = PolType, width = Width, sub = Sub))
        if YesNoShowPlots > 0:
            plt.pause(2)
        plt.close()              

        Q = Horz_Data['Q']
        Q_mean = Horz_Data['Q_Mean']
        Q_Unc = Horz_Data['Q_Unc']
        Shadow = Horz_Data['Shadow']
        if HaveDiagData == 1:
            text_output = np.array([Q, Struc, Struc_Unc, M_Perp, M_Perp_Unc, M_Parl_NSF, M_Parl_NSF_Unc, M_Parl_SF, M_Parl_SF_Unc, Q_Unc, Q_mean, Shadow])
            text_output = text_output.T
            np.savetxt(save_path + 'ResultsFullPol_{samp},{cf}_{key}{width}{sub}.txt'.format(samp=Sample, cf = Config, key = PolType, width = Width, sub = Sub), text_output,
                   delimiter = ' ', comments = ' ', header= 'Q, Struc, DelStruc, M_Perp, DelM_Perp, M_Parl_NSF, DelM_Parl_NSF, M_Parl_SF, DelM_Parl_SF, Q_Unc, Q_mean, Shadow', fmt='%1.4e')
        else:
            text_output = np.array([Q, Struc, Struc_Unc, M_Perp, M_Perp_Unc, M_Parl_NSF, M_Parl_NSF_Unc, Q_Unc, Q_mean, Shadow])
            text_output = text_output.T
            np.savetxt(save_path + 'ResultsFullPol_{samp},{cf}_{key}{width}{sub}.txt'.format(samp=Sample, cf = Config, key = PolType, width = Width, sub = Sub), text_output,
                   delimiter = ' ', comments = ' ', header= 'Q, Struc, DelStruc, M_Perp, DelM_Perp, M_Parl_NSF, DelM_Parl_NSF, Q_Unc, Q_mean, Shadow', fmt='%1.4e')
            
    Results = {}
    Results['QCirc'] = Circ_Data['Q']
    Results['CircSum'] = Circ_Sum
    Results['CircSum_Unc'] = Circ_Sum_Unc
    Results['QHorzVert'] = Horz_Data['Q']
    Results['M_Perp'] = M_Perp
    Results['M_Perp_Unc'] = M_Perp_Unc
    Results['M_Parl_NSF'] = M_Parl_NSF
    Results['M_Parl_NSF_Unc'] = M_Parl_NSF_Unc
    
    return Results

def vSANS_ProcessHalfPolSlices(PolSampleSlices, Sample, PolEmptySlices):
    '''Note uses AutoSubtractEmpty  and UseMTCirc from UserInput.py'''

    Sub = ""

    Vert_Data = {}
    Horz_Data = {}
    Circ_Data = {}
    MT = {}
    MTCirc = {}
    HaveMTCirc = 0
    HaveVertData = 0
    HaveHorzData = 0
    HaveCircData = 0

    if "Circ" in Slices:
        slice_details = "CircAve"
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveCircData = 1
        Circ_Data['Q'] = PolSampleSlices[Sample][slice_details]['U']['Q']
        Circ_Data['U'] = PolSampleSlices[Sample][slice_details]['U']['I']
        Circ_Data['U_Unc'] = PolSampleSlices[Sample][slice_details]['U']['I_Unc']
        Circ_Data['D'] = PolSampleSlices[Sample][slice_details]['D']['I']
        Circ_Data['D_Unc'] = PolSampleSlices[Sample][slice_details]['D']['I_Unc']
        Circ_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['U']['Q_Mean']
        Circ_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['U']['Q_Uncertainty']
        Circ_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['U']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                HaveMTCirc = 1
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['U']['Q']
                MT['U'] = PolEmptySlices['Empty'][slice_details]['U']['I']
                MT['U_Unc'] = PolEmptySlices['Empty'][slice_details]['U']['I_Unc']
                MT['D'] = PolEmptySlices['Empty'][slice_details]['D']['I']
                MT['D_Unc'] = PolEmptySlices['Empty'][slice_details]['D']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['U']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['U']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['U']['Shadow']
                MTCirc = MT

                CircMatch, MTMatch = MatchQ_PADataSets(Circ_Data, MT, 1)
                Circ_Data = Subtract_PADataSets(CircMatch, MTMatch, 1)

        #SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Circ_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        #PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Circ_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''
        Circ_Sum = (Circ_Data['U'] + Circ_Data['D'])/2.0
        Circ_Sum_Unc = (np.sqrt(np.power(Circ_Data['U_Unc'],2) + np.power(Circ_Data['D_Unc'],2)))/2.0

    if "Horz" in Slices:
        slice_details = "Horz"+str(SectorCutAngles)
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveHorzData = 1
        Horz_Data['Q'] = PolSampleSlices[Sample][slice_details]['U']['Q']
        Horz_Data['U'] = PolSampleSlices[Sample][slice_details]['U']['I']
        Horz_Data['U_Unc'] = PolSampleSlices[Sample][slice_details]['U']['I_Unc']
        Horz_Data['D'] = PolSampleSlices[Sample][slice_details]['D']['I']
        Horz_Data['D_Unc'] = PolSampleSlices[Sample][slice_details]['D']['I_Unc']
        Horz_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['U']['Q_Mean']
        Horz_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['U']['Q_Uncertainty']
        Horz_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['U']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['U']['Q']
                MT['U'] = PolEmptySlices['Empty'][slice_details]['U']['I']
                MT['U_Unc'] = PolEmptySlices['Empty'][slice_details]['U']['I_Unc']
                MT['D'] = PolEmptySlices['Empty'][slice_details]['D']['I']
                MT['D_Unc'] = PolEmptySlices['Empty'][slice_details]['D']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['U']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['U']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['U']['Shadow']

                if UseMTCirc == 1 and HaveMTCirc == 1:
                    HorzMatch, MTMatch = MatchQ_PADataSets(Horz_Data, MTCirc, 1)
                else:
                    HorzMatch, MTMatch = MatchQ_PADataSets(Horz_Data, MT, 1)
                Horz_Data = Subtract_PADataSets(HorzMatch, MTMatch, 1)

        #SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Horz_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        #PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Horz_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''

    if "Vert" in Slices:
        slice_details = "Vert"+str(SectorCutAngles)
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveVertData = 1
        Vert_Data['Q'] = PolSampleSlices[Sample][slice_details]['U']['Q']
        Vert_Data['U'] = PolSampleSlices[Sample][slice_details]['U']['I']
        Vert_Data['U_Unc'] = PolSampleSlices[Sample][slice_details]['U']['I_Unc']
        Vert_Data['D'] = PolSampleSlices[Sample][slice_details]['D']['I']
        Vert_Data['D_Unc'] = PolSampleSlices[Sample][slice_details]['D']['I_Unc']
        Vert_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['U']['Q_Mean']
        Vert_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['U']['Q_Uncertainty']
        Vert_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['U']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['U']['Q']
                MT['U'] = PolEmptySlices['Empty'][slice_details]['U']['I']
                MT['U_Unc'] = PolEmptySlices['Empty'][slice_details]['U']['I_Unc']
                MT['D'] = PolEmptySlices['Empty'][slice_details]['D']['I']
                MT['D_Unc'] = PolEmptySlices['Empty'][slice_details]['D']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['U']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['U']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['U']['Shadow']

                if UseMTCirc == 1 and HaveMTCirc == 1:
                    VertMatch, MTMatch = MatchQ_PADataSets(Vert_Data, MTCirc, 1)
                else:
                    VertMatch, MTMatch = MatchQ_PADataSets(Vert_Data, MT, 1)
                Vert_Data = Subtract_PADataSets(VertMatch, MTMatch, 1)

        #SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Vert_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        #PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Vert_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''

    if HaveHorzData == 1 and HaveVertData == 1:

        HorzMatch, VertMatch = MatchQ_PADataSets(Horz_Data, Vert_Data, 1)
        for entry in Horz_Data:
            Horz_Data[entry] = HorzMatch[entry]
        for entry in Vert_Data:
            Vert_Data[entry] = VertMatch[entry]

        M_Parl_Sub = (Vert_Data['D'] + Vert_Data['U'] - (Horz_Data['D'] + Horz_Data['U']) )/2.0
        M_Parl_Sub_Unc = np.sqrt(np.power(Vert_Data['D_Unc'],2) + np.power(Vert_Data['U_Unc'],2) + np.power(Horz_Data['D_Unc'],2) + np.power(Horz_Data['U_Unc'],2))/2.0

        Struc = (Horz_Data['D'] + Horz_Data['U'])/2.0
        Struc_Unc = np.sqrt(np.power(Horz_Data['D_Unc'],2) + np.power(Horz_Data['U_Unc'],2))/2.0

        Diff = Vert_Data['D'] - Vert_Data['U']
        Diff_Unc = np.sqrt(np.power(Vert_Data['D_Unc'],2) + np.power(Vert_Data['U_Unc'],2))
        Num = np.power((Diff),2)
        Num_Unc = np.sqrt(2.0)*Diff*Diff_Unc
        Denom = (4.0*(Horz_Data['D'] + Horz_Data['U']))
        Denom_Unc = np.sqrt(np.power(Horz_Data['D_Unc'],2) + np.power(Horz_Data['U_Unc'],2))
        M_Parl_Div = (Num / Denom)/2.0
        M_Parl_Div_Unc = M_Parl_Div * np.sqrt( np.power(Num_Unc,2)/np.power(Num,2) + np.power(Denom_Unc,2)/np.power(Denom,2))

        Width = str(SectorCutAngles) + "Deg"
        fig = plt.figure()
        ax = plt.axes()
        ax.set_xscale("log")
        ax.set_yscale("log")
        if YesNoSetPlotYRange > 0:
            ax.set_ylim(bottom = PlotYmin, top = PlotYmax)
        if YesNoSetPlotXRange > 0:
            ax.set_xlim(left = PlotXmin, right = PlotXmax)
        ax.errorbar(Horz_Data['Q'], M_Parl_Sub, yerr=M_Parl_Sub_Unc, fmt = 'b*', label='M_Parl (subtraction)')
        ax.errorbar(Horz_Data['Q'], M_Parl_Div, yerr=M_Parl_Div_Unc, fmt = 'g*', label='M_Parl (dividion)')
        ax.errorbar(Horz_Data['Q'], Struc, yerr=Struc_Unc, fmt = 'r*', label='Structural (horizontal)')
        plt.xlabel('Q (inverse angstroms)')
        plt.ylabel('Intensity')
        plt.title('Magnetic and Structural Scattering of {samp}'.format(samp=Sample))
        plt.legend()
        fig.savefig(save_path + 'ResultsHalfPol_{samp},{cf}_{width}{sub}.png'.format(samp=Sample, cf = Config, width = Width, sub = Sub))
        if YesNoShowPlots > 0:
            plt.pause(2)
        plt.close()              

        Q = Horz_Data['Q']
        Q_mean = Horz_Data['Q_Mean']
        Q_Unc = Horz_Data['Q_Unc']
        Shadow = Horz_Data['Shadow']
        text_output = np.array([Q, Struc, Struc_Unc, M_Parl_Div, M_Parl_Div_Unc, M_Parl_Sub, M_Parl_Sub_Unc, Q_Unc, Q_mean, Shadow])
        text_output = text_output.T
        np.savetxt(save_path + 'ResultsHalfPol_{samp},{cf}_{width}{sub}.txt'.format(samp=Sample, cf = Config, width = Width, sub = Sub), text_output,
               delimiter = ' ', comments = ' ', header= 'Q, Struc, DelStruc, M_Parl_Div, DelM_Parl_Div, M_Parl_Sub, DelM_Parl_Sub, Q_Unc, Q_mean, Shadow', fmt='%1.4e')

    Results = {}
    Results['QCirc'] = Circ_Data['Q']
    Results['CircSum'] = Circ_Sum
    Results['CircSum_Unc'] = Circ_Sum_Unc
    
    return Results

def vSANS_ProcessUnpolSlices(PolSampleSlices, Sample, PolEmptySlices):
    '''Note uses AutoSubtractEmpty  and UseMTCirc from UserInput.py'''

    Sub = ""

    Vert_Data = {}
    Horz_Data = {}
    Circ_Data = {}
    MT = {}
    MTCirc = {}
    HaveMTCirc = 0
    HaveVertData = 0
    HaveHorzData = 0
    HaveCircData = 0

    if "Circ" in Slices:
        slice_details = "CircAve"
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveCircData = 1
        Circ_Data['Q'] = PolSampleSlices[Sample][slice_details]['Unpol']['Q']
        Circ_Data['Unpol'] = PolSampleSlices[Sample][slice_details]['Unpol']['I']
        Circ_Data['Unpol_Unc'] = PolSampleSlices[Sample][slice_details]['Unpol']['I_Unc']
        Circ_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['Unpol']['Q_Mean']
        Circ_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['Unpol']['Q_Uncertainty']
        Circ_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['Unpol']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                HaveMTCirc = 1
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Q']
                MT['Unpol'] = PolEmptySlices['Empty'][slice_details]['Unpol']['I']
                MT['Unpol_Unc'] = PolEmptySlices['Empty'][slice_details]['Unpol']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Shadow']
                MTCirc = MT

                CircMatch, MTMatch = MatchQ_PADataSets(Circ_Data, MT, 0)
                Circ_Data = Subtract_PADataSets(CircMatch, MTMatch, 0)

        #SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Circ_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        #PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Circ_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''
        Circ_Sum = Circ_Data['Unpol']
        Circ_Sum_Unc = Circ_Data['Unpol_Unc']

    if "Horz" in Slices:
        slice_details = "Horz"+str(SectorCutAngles)
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveHorzData = 1
        Horz_Data['Q'] = PolSampleSlices[Sample][slice_details]['Unpol']['Q']
        Horz_Data['Unpol'] = PolSampleSlices[Sample][slice_details]['Unpol']['I']
        Horz_Data['Unpol_Unc'] = PolSampleSlices[Sample][slice_details]['Unpol']['I_Unc']
        Horz_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['Unpol']['Q_Mean']
        Horz_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['Unpol']['Q_Uncertainty']
        Horz_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['Unpol']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Q']
                MT['Unpol'] = PolEmptySlices['Empty'][slice_details]['Unpol']['I']
                MT['Unpol_Unc'] = PolEmptySlices['Empty'][slice_details]['Unpol']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Shadow']

                if UseMTCirc == 1 and HaveMTCirc == 1:
                    HorzMatch, MTMatch = MatchQ_PADataSets(Horz_Data, MTCirc, 0)
                else:
                    HorzMatch, MTMatch = MatchQ_PADataSets(Horz_Data, MT, 0)
                Horz_Data = Subtract_PADataSets(HorzMatch, MTMatch, 0)

        #SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Horz_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        #PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Horz_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''

    if "Vert" in Slices:
        slice_details = "Vert"+str(SectorCutAngles)
        PolType = PolSampleSlices[Sample][slice_details]['PolType']
        HaveVertData = 1
        Vert_Data['Q'] = PolSampleSlices[Sample][slice_details]['Unpol']['Q']
        Vert_Data['Unpol'] = PolSampleSlices[Sample][slice_details]['Unpol']['I']
        Vert_Data['Unpol_Unc'] = PolSampleSlices[Sample][slice_details]['Unpol']['I_Unc']
        Vert_Data['Q_Mean'] = PolSampleSlices[Sample][slice_details]['Unpol']['Q_Mean']
        Vert_Data['Q_Unc'] = PolSampleSlices[Sample][slice_details]['Unpol']['Q_Uncertainty']
        Vert_Data['Shadow'] = PolSampleSlices[Sample][slice_details]['Unpol']['Shadow']

        if 'Empty' in PolEmptySlices and AutoSubtractEmpty == 1:
            if PolType in PolEmptySlices['Empty'][slice_details]['PolType']:
                Sub = ",SubMT"
                MT['Q'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Q']
                MT['Unpol'] = PolEmptySlices['Empty'][slice_details]['Unpol']['I']
                MT['Unpol_Unc'] = PolEmptySlices['Empty'][slice_details]['Unpol']['I_Unc']
                MT['Q_Mean'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Q_Mean']
                MT['Q_Unc'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Q_Uncertainty']
                MT['Shadow'] = PolEmptySlices['Empty'][slice_details]['Unpol']['Shadow']

                if UseMTCirc == 1 and HaveMTCirc == 1:
                    VertMatch, MTMatch = MatchQ_PADataSets(Vert_Data, MTCirc, 0)
                else:
                    VertMatch, MTMatch = MatchQ_PADataSets(Vert_Data, MT, 0)
                Vert_Data = Subtract_PADataSets(VertMatch, MTMatch, 0)

        #SaveTextDataFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Vert_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.txt'''
        #PlotFourCombinedCrossSections('{corr}'.format(corr = PolType), slice_details, Sub, Sample, Config, Vert_Data)
        '''saves data as SliceFullPol_{samp},{cf}_{corr}{slice_key}.png'''

    if HaveHorzData == 1 and HaveVertData == 1:

        HorzMatch, VertMatch = MatchQ_PADataSets(Horz_Data, Vert_Data, 0)
        for entry in Horz_Data:
            Horz_Data[entry] = HorzMatch[entry]
        for entry in Vert_Data:
            Vert_Data[entry] = VertMatch[entry]

        M_Parl_Sub = Vert_Data['Unpol'] - Horz_Data['Unpol']
        M_Parl_Sub_Unc = np.sqrt(np.power(Vert_Data['Unpol_Unc'],2) + np.power(Horz_Data['Unpol_Unc'],2))

        Struc = Horz_Data['Unpol']
        Struc_Unc = Horz_Data['Unpol_Unc']

        Width = str(SectorCutAngles) + "Deg"
        fig = plt.figure()
        ax = plt.axes()
        ax.set_xscale("log")
        ax.set_yscale("log")
        if YesNoSetPlotYRange > 0:
            ax.set_ylim(bottom = PlotYmin, top = PlotYmax)
        if YesNoSetPlotXRange > 0:
            ax.set_xlim(left = PlotXmin, right = PlotXmax)
        ax.errorbar(Horz_Data['Q'], M_Parl_Sub, yerr=M_Parl_Sub_Unc, fmt = 'b*', label='M_Parl (subtraction)')
        ax.errorbar(Horz_Data['Q'], Struc, yerr=Struc_Unc, fmt = 'r*', label='Structural (horizontal)')
        plt.xlabel('Q (inverse angstroms)')
        plt.ylabel('Intensity')
        plt.title('Magnetic and Structural Scattering of {samp}'.format(samp=Sample))
        plt.legend()
        fig.savefig(save_path + 'ResultsUnpol_{samp},{cf}_{width}{sub}.png'.format(samp=Sample, cf = Config, width = Width, sub = Sub))
        if YesNoShowPlots > 0:
            plt.pause(2)
        plt.close()              

        Q = Horz_Data['Q']
        Q_mean = Horz_Data['Q_Mean']
        Q_Unc = Horz_Data['Q_Unc']
        Shadow = Horz_Data['Shadow']
        text_output = np.array([Q, Struc, Struc_Unc, M_Parl_Sub, M_Parl_Sub_Unc, Q_Unc, Q_mean, Shadow])
        text_output = text_output.T
        np.savetxt(save_path + 'ResultsUnpol_{samp},{cf}_{width}{sub}.txt'.format(samp=Sample, cf = Config, width = Width, sub = Sub), text_output,
               delimiter = ' ', comments = ' ', header= 'Q, Struc, DelStruc, M_Parl_Sub, DelM_Parl_Sub, Q_Unc, Q_mean, Shadow', fmt='%1.4e')

    Results = {}
    Results['QCirc'] = Circ_Data['Q']
    Results['CircSum'] = Circ_Sum
    Results['CircSum_Unc'] = Circ_Sum_Unc
    
    return Results


def vSANS_Record_DataProcessing(Contents, Plex_Name, Mask_Record, Scatt, BlockBeam, Trans, Pol_Trans, HE3_Cell_Summary):
                                
    file1 = open(save_path + "DataReductionSummary.txt","w+")
    file1.write("Record of Data Reduction \n")
    file1.write("****************************************** \n")
    file1.write("****************************************** \n")
    file1.write("User-defined Inputs: \n")
    file1.write('\n')
    file1.write(Contents)
    file1.write("****************************************** \n")
    file1.write("****************************************** \n")
    file1.write('\n')

    if YesNoManualHe3Entry >= 1:
        file1.write("New_HE3_Files = ")
        for x in New_HE3_Files:
            file1.write(str(x) + ' ')
        file1.write('\n')
        file1.write("MuValues = ")
        for x in MuValues:
            file1.write(str(x) + ' ')
        file1.write('\n')
        file1.write("TeValues = ")
        for x in TeValues:
            file1.write(str(x) + ' ')
        file1.write('\n')
    file1.write('\n')
    file1.write('Plex file is ' + str(Plex_Name) + '\n')
    file1.write('\n')
    file1.write('Detector shadowing is automatically corrected for. \n')
    file1.write('Additional users masks may be added; they are (if present): \n')
    for Config in Mask_Record:
        file1.write('Configuration: ' + str(Config) + '\n')
        file1.write('   Trans Mask: ' + str(Mask_Record[Config]['Trans']) + '\n')
        file1.write('   Scatt Mask: ' + str(Mask_Record[Config]['Scatt_Standard']) + '\n')
        file1.write('   Scatt Mask w/ solenoid: ' + str(Mask_Record[Config]['Scatt_WithSolenoid']) + '\n')
        file1.write('\n')
        
    for Sample in Scatt:
        file1.write(str(Sample) +  '(' +  str(Scatt[Sample]['Intent']) + ') \n')
        for Config in Scatt[Sample]['Config(s)']:
            file1.write(' Config:' + str(Config) + '\n')
            if Config in BlockBeam:
                str1 = str(BlockBeam[Config]['Scatt']['File'])
                str2 = str(BlockBeam[Config]['Trans']['File'])
                str3 = '  Block Beam: '
                file1.write(str3)
                if str(BlockBeam[Config]['Scatt']['File']).find('NA') == -1 and str(BlockBeam[Config]['Trans']['File']).find('NA') == -1:
                    file1.write(str1)
                    file1.write(' (Scatt) and (Trans) ')
                    file1.write(str2)
                    file1.write('\n')
                elif str(BlockBeam[Config]['Scatt']['File']).find('NA') == -1 and str(BlockBeam[Config]['Trans']['File']).find('NA') != -1:
                    file1.write(str1)
                    file1.write('\n')
                elif str(BlockBeam[Config]['Scatt']['File']).find('NA') != -1 and str(BlockBeam[Config]['Trans']['File']).find('NA') == -1:
                    file1.write(str2)
                    file1.write('\n')
            else:
                str4 = '      ' + 'Block Beam Scatt, Trans files are not available \n'
                file1.write(str4)
            TransUnpol = str(Trans[Sample]['Config(s)'][Config]['Unpol_Files'][0])
            if TransUnpol.find('N') != -1:
                TransUnpol = 'NA'
            TransPol = str(Trans[Sample]['Config(s)'][Config]['U_Files'][0])
            if TransPol.find('N') != -1:
                TransPol = 'NA'
            file1.write('  Unpol, pol scaling trans: ' + TransUnpol + ' , ' + TransPol + '\n')
            file1.write('  Unpolarized Scatt ' + str(Scatt[Sample]['Config(s)'][Config]['Unpol']) + '\n')
            file1.write('  Up Scatt ' + str(Scatt[Sample]['Config(s)'][Config]['U']) + '\n')
            file1.write('  Down Scatt ' + str(Scatt[Sample]['Config(s)'][Config]['D']) + '\n')
            file1.write('  Up-Up Scatt ' + str(Scatt[Sample]['Config(s)'][Config]['UU']) + '\n')
            file1.write('  Up-Down Scatt ' + str(Scatt[Sample]['Config(s)'][Config]['UD']) + '\n')
            file1.write('  Down-Down Scatt ' + str(Scatt[Sample]['Config(s)'][Config]['DD']) + '\n')
            file1.write('  Down-Up Scatt '+ str(Scatt[Sample]['Config(s)'][Config]['DU']) + '\n')
        if Sample in Pol_Trans:
            if 'P_SM' in Pol_Trans[Sample] and str(Pol_Trans[Sample]['P_SM']).find('NA') == -1:
                file1.write(' Full Polarization Results: \n')
                pol_num = int(Pol_Trans[Sample]['P_SM']*10000)/10000
                file1.write(' P_SM  x Depol: ' + str(pol_num) + '\n')
                file1.write(' UU Trans ' + str(Pol_Trans[Sample]['T_UU']['File']) + '\n')
                file1.write(' DU Trans ' + str(Pol_Trans[Sample]['T_DU']['File']) + '\n')
                file1.write(' DD Trans ' + str(Pol_Trans[Sample]['T_DD']['File']) + '\n')
                file1.write(' UD Trans ' + str(Pol_Trans[Sample]['T_UD']['File']) + '\n')
                file1.write(' SM Trans ' + str(Pol_Trans[Sample]['T_SM']['File']) + '\n')
        file1.write(' \n')

    for entry in HE3_Cell_Summary:
        file1.write('3He Cell: ' + str(HE3_Cell_Summary[entry]['Name']) + '\n')
        file1.write('Lifetime (hours): ' + str(HE3_Cell_Summary[entry]['Gamma(hours)']) + ' +/- ' + str(HE3_Cell_Summary[entry]['Gamma_Unc']) + '\n')
        file1.write('Atomic P_0: ' + str(HE3_Cell_Summary[entry]['Atomic_P0']) + ' +/- ' + str(HE3_Cell_Summary[entry]['Atomic_P0_Unc']) + '\n')
        file1.write('Neutron P_0: ' + str(HE3_Cell_Summary[entry]['Neutron_P0']) + ' +/- ' + str(HE3_Cell_Summary[entry]['Neutron_P0_Unc']) + '\n')
        file1.write('\n')
    file1.close()

    return

def Annular_Average(Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_total, GeneralMask, ScaledData, ScaledData_Unc):

    relevant_detectors = short_detectors
    AverageQRanges = 1
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors
        AverageQRanges = 0

    Q_Mask = {}
    for dshort in relevant_detectors:
        QBorder = np.ones_like(Q_total[dshort])
        QBorder[Q_total[dshort] < Q_min] = 0.0
        QBorder[Q_total[dshort] > Q_max] = 0.0
        Q_Mask[dshort] = QBorder

    
    Counts = -101
    Deg = -101
    BothSides = 0
    PlotYesNo = 0
    for x in range(0, 72):
        degree = x*5
        Sector_Mask = SectorMask_AllDetectors(InPlaneAngleMap, degree, 2.5, BothSides)

        summed_pixels = 0
        summed_intensity = 0
        for dshort in relevant_detectors:
            pixel_counts = Sector_Mask[dshort]*Q_Mask[dshort]*GeneralMask[dshort]
            intensity_counts = pixel_counts*ScaledData[dshort]
            summed_pixels = summed_pixels + np.sum(pixel_counts)
            summed_intensity = summed_intensity + np.sum(intensity_counts)
        ratio = summed_intensity/summed_pixels
        if Counts == -101 and summed_pixels > 0:
            Counts = [ratio]
            Deg = [degree]
        elif summed_pixels > 0:
            Counts.append(ratio)
            Deg.append(degree)

    xdata = np.array(Deg)
    ydata = np.array(Counts)
    fig = plt.figure()
    plt.plot(xdata, ydata, 'b*-', label='Annular_Average')
    plt.xscale('linear')
    plt.yscale('linear')
    plt.xlabel('Angle (degrees)')
    plt.ylabel('Summed Counts')
    plt.title('Annular Average_{qmin}to{qmax}invang'.format(qmin = Q_min, qmax = Q_max))
    plt.legend()
    fig.savefig(save_path + 'AnnularAverage_{idnum},{cf}.png'.format(idnum=Sample, cf = Config))
    plt.pause(2)
    plt.close()
    
    
    return

def getVarFromFile(filename):
    import imp
    f = open(filename)
    global data
    data = imp.load_source('data', '', f)
    f.close()

    return

def RemoveMainBeamFullPol(Scatt_Type, Sample, Config, Scatt, HE3_Cell_Summary, ScaledData, ScaledData_Unc, OpenScaledData, OpenScaledData_Unc):

    relevant_detectors = short_detectors
    if str(Config).find('CvB') != -1:
        relevant_detectors = all_detectors

    type_time = Scatt_Type + "_Time"
    filenumber_counter = 0
    AveHe3Trans = 0
    for filenumber in Scatt[Sample]['Config(s)'][Config][Scatt_Type]:
        f = get_by_filenumber(representative_filenumber)
        if f is not None:
            entry = Scatt[Sample]['Config(s)'][Config][type_time][filenumber_counter]
            NP, UT, T_MAJ, T_MIN = HE3_Pol_AtGivenTime(entry, HE3_Cell_Summary)
            AveHe3Trans += T_MAJ
            filenumber_counter += 1
            
    if filenumber_counter > 0:
        AveHe3Trans = AveHe3Trans / filenumber_counter
        for dshort in relevant_detectors:
            #Kludge 2
            ScaledData[dshort] = ScaledData[dshort] - OpenScaledData[dshort]*AveHe3Trans
        
    return ScaledData, ScaledData_Unc
#*************************************************
#***        Start of 'The Program'             ***
#*************************************************
h = open("UserInput.py","r")
if h.mode == "r":
    Contents = h.read()
    #print(contents)
h.close()

if not os.path.exists(save_path):
    os.makedirs(save_path)

'''System based on categorizing/grouping files:'''
Sample_Names, Sample_Bases, Configs, BlockBeamCatalog, ScattCatalog, TransCatalog, Pol_TransCatalog, HE3_TransCatalog, start_number, filenumberlisting = VSANS_SortDataAutomatic(YesNoManualHe3Entry, New_HE3_Files, MuValues, TeValues)
VSANS_ShareSampleBaseTransCatalog(TransCatalog, ScattCatalog)
VSANS_ShareEmptyPolBeamScattCatalog(ScattCatalog)
VSANS_ProcessHe3TransCatalog(HE3_TransCatalog, BlockBeamCatalog, TransPanel)
VSANS_ProcessPolTransCatalog(Pol_TransCatalog, BlockBeamCatalog, TransPanel)
VSANS_ProcessTransCatalog(TransCatalog, BlockBeamCatalog, TransPanel)
#Make sure blockbeam subtraction is working correctly...
#How to handle cases where don't have complete cross-sections; maybe streamline vSANS_FullPolSlices, vSANS_HalfPolSlices, vSANS_UnpolSlices
UserDefinedMasks, Mask_Record = ReadIn_IGORMasks(filenumberlisting)
Plex_Name, Plex = Plex_File(start_number)
HE3_Cell_Summary = HE3_DecayCurves(HE3_TransCatalog)
vSANS_PolarizationSupermirrorAndFlipper(Pol_TransCatalog, HE3_Cell_Summary, UsePolCorr)
Truest_PSM = vSANS_BestSuperMirrorPolarizationValue(PSM_Guess, YesNoBypassBestGuessPSM, Pol_TransCatalog)
vSANS_Record_DataProcessing(Contents, Plex_Name, Mask_Record, ScattCatalog, BlockBeamCatalog, TransCatalog, Pol_TransCatalog, HE3_Cell_Summary)

GeneralMaskWOSolenoid = {}
GeneralMaskWSolenoid = {}
QValues_All = {}
for Config in Configs:
    representative_filenumber = Configs[Config]
    if representative_filenumber != 0: #and str(Config).find('CvB') != -1:
        Solid_Angle = SolidAngle_AllDetectors(representative_filenumber, Config)
        BBList = [0]
        if Config in BlockBeamCatalog:
            if 'NA' not in BlockBeamCatalog[Config]['Trans']['File']:
                BBList = BlockBeamCatalog[Config]['Trans']['File']
            elif 'NA' not in BlockBeamCatalog[Config]['Scatt']['File']:
                BBList = BlockBeamCatalog[Config]['Scatt']['File']
        BB_per_second, BBUnc_per_second = VSANS_BlockedBeamCountsPerSecond_ListOfFiles(BBList, Config, representative_filenumber)
        Qx, Qy, Qz, Q_total, Q_perp_unc, Q_parl_unc, InPlaneAngleMap, dimXX, dimYY, Shadow_Mask = QCalculation_AllDetectors(representative_filenumber, Config)
        QValues_All = {'QX':Qx,'QY':Qy,'QZ':Qz,'Q_total':Q_total,'Q_perp_unc':Q_perp_unc,'Q_parl_unc':Q_parl_unc}
        Q_min, Q_max, Q_bins = MinMaxQ(Q_total, Config)
                    
        relevant_detectors = short_detectors
        if str(Config).find('CvB') != -1:
            relevant_detectors = all_detectors
            
        for dshort in relevant_detectors:
            GeneralMaskWOSolenoid[dshort] = Shadow_Mask[dshort]
            GeneralMaskWSolenoid[dshort] = Shadow_Mask[dshort]
        if Config in UserDefinedMasks:
            if 'NA' not in UserDefinedMasks[Config]['Scatt_WithSolenoid']:
                for dshort in relevant_detectors:
                    GeneralMaskWSolenoid[dshort] = Shadow_Mask[dshort]*UserDefinedMasks[Config]['Scatt_WithSolenoid'][dshort]          
            if 'NA' not in UserDefinedMasks[Config]['Scatt_Standard']:
                for dshort in relevant_detectors:
                    GeneralMaskWOSolenoid[dshort] = Shadow_Mask[dshort]*UserDefinedMasks[Config]['Scatt_Standard'][dshort]
                        

        FullPolSampleSlices = {}
        FullPolEmptySlices = {}
        HalfPolSampleSlices = {}
        HalfPolEmptySlices = {}
        UnpolSampleSlices = {}
        UnpolEmptySlices = {}
        for Sample in Sample_Names:
            if Sample in ScattCatalog:                
                if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1 or str(ScattCatalog[Sample]['Intent']).find('Empty') != -1:

                    UUScaledData, UUScaledData_Unc = AbsScale('UU', Sample, Config, BB_per_second, Solid_Angle, Plex, ScattCatalog, TransCatalog)
                    DUScaledData, DUScaledData_Unc = AbsScale('DU', Sample, Config, BB_per_second, Solid_Angle, Plex, ScattCatalog, TransCatalog)
                    DDScaledData, DDScaledData_Unc = AbsScale('DD', Sample, Config, BB_per_second, Solid_Angle, Plex, ScattCatalog, TransCatalog)
                    UDScaledData, UDScaledData_Unc = AbsScale('UD', Sample, Config, BB_per_second, Solid_Angle, Plex, ScattCatalog, TransCatalog)
                    FullPolGo = 0
                    if 'NA' not in UUScaledData and 'NA' not in DUScaledData and 'NA' not in DDScaledData and 'NA' not in UDScaledData:

                        
                        representative_filenumber = ScattCatalog[Sample]['Config(s)'][Config]['UU'][0]
                        Qx, Qy, Qz, Q_total, Q_perp_unc, Q_parl_unc, InPlaneAngleMap, dimXX, dimYY, Shadow_Mask = QCalculation_AllDetectors(representative_filenumber, Config)
                        QValues_All = {'QX':Qx,'QY':Qy,'QZ':Qz,'Q_total':Q_total,'Q_perp_unc':Q_perp_unc,'Q_parl_unc':Q_parl_unc}
                        FullPolGo, PolCorrUU, PolCorrDU, PolCorrDD, PolCorrUD, PolCorrUU_Unc, PolCorrDU_Unc, PolCorrDD_Unc, PolCorrUD_Unc = vSANS_PolCorrScattFiles(Truest_PSM, dimXX, dimYY, Sample, Config, ScattCatalog, TransCatalog, Pol_TransCatalog, UUScaledData, DUScaledData, DDScaledData, UDScaledData, UUScaledData_Unc, DUScaledData_Unc, DDScaledData_Unc, UDScaledData_Unc)

                        if YesNo_2DCombinedFiles > 0:
                            if FullPolGo >= 2:
                                ASCIIlike_Output('PolCorrUU', Sample, Config, PolCorrUU, PolCorrUU_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('PolCorrDU', Sample, Config, PolCorrDU, PolCorrDU_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('PolCorrDD', Sample, Config, PolCorrDD, PolCorrDD_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('PolCorrUD', Sample, Config, PolCorrUD, PolCorrUD_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('PolCorrSumAllCS', Sample, Config, UnpolEquiv, UnpolEquiv_Unc, QValues_All, GeneralMaskWSolenoid)
                            elif FullPolGo >= 1 and FullPolGo < 2:
                                ASCIIlike_Output('He3CorrUU', Sample, Config, PolCorrUU, PolCorrUU_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('He3CorrDU', Sample, Config, PolCorrDU, PolCorrDU_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('He3CorrDD', Sample, Config, PolCorrDD, PolCorrDD_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('He3CorrUD', Sample, Config, PolCorrUD, PolCorrUD_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('He3CorrSumAllCS', Sample, Config, UnpolEquiv, UnpolEquiv_Unc, QValues_All, GeneralMaskWSolenoid)
                            else:
                                ASCIIlike_Output('NotCorrUU', Sample, Config, UUScaledData, UUScaledData_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('NotCorrDU', Sample, Config, DUScaledData, DUScaledData_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('NotCorrDD', Sample, Config, DDScaledData, DDScaledData_Unc, QValues_All, GeneralMaskWSolenoid)
                                ASCIIlike_Output('NotCorrUD', Sample, Config, UDScaledData, UDScaledData_Unc, QValues_All, GeneralMaskWSolenoid)

                        if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                            FullPolSampleSlices[Sample] = vSANS_FullPolSlices(FullPolGo, Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, PolCorrUU, PolCorrUU_Unc, PolCorrDU, PolCorrDU_Unc, PolCorrDD, PolCorrDD_Unc, PolCorrUD, PolCorrUD_Unc)
                        if str(ScattCatalog[Sample]['Intent']).find('Empty') != -1:
                            FullPolEmptySlices['Empty'] = vSANS_FullPolSlices(FullPolGo, Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, PolCorrUU, PolCorrUU_Unc, PolCorrDU, PolCorrDU_Unc, PolCorrDD, PolCorrDD_Unc, PolCorrUD, PolCorrUD_Unc)
                    
                    UScaledData, UScaledData_Unc = AbsScale('U', Sample, Config, BB_per_second, Solid_Angle, Plex, ScattCatalog, TransCatalog)
                    DScaledData, DScaledData_Unc = AbsScale('D', Sample, Config, BB_per_second, Solid_Angle, Plex, ScattCatalog, TransCatalog)
                    if 'NA' not in UScaledData and 'NA' not in DScaledData:
                        if YesNo_2DCombinedFiles > 0:
                            representative_filenumber = Scatt[Sample]['Config(s)'][Config]['U'][0]
                            Qx, Qy, Qz, Q_total, Q_perp_unc, Q_parl_unc, InPlaneAngleMap, dimXX, dimYY, Shadow_Mask = QCalculation_AllDetectors(representative_filenumber, Config)
                            QValues_All = {'QX':Qx,'QY':Qy,'QZ':Qz,'Q_total':Q_total,'Q_perp_unc':Q_perp_unc,'Q_parl_unc':Q_parl_unc}
                            ASCIIlike_Output('U', Sample, Config, UScaledData, UScaledData_Unc, QValues_All, GeneralMaskWOSolenoid)
                            ASCIIlike_Output('D', Sample, Config, DScaledData, DScaledData_Unc, QValues_All, GeneralMaskWOSolenoid)
                            ASCIIlike_Output('DMinusU', Sample, Config, DiffData, DiffData_Unc, QValues_All, GeneralMaskWOSolenoid)
                            ASCIIlike_Output('DPlusU', Sample, Config, SumData, SumData_Unc, QValues_All, GeneralMaskWOSolenoid)
                        if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                            HalfPolSampleSlices[Sample] = vSANS_HalfPolSlices('HalfPol', Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, UScaledData, UScaledData_Unc, DScaledData, DScaledData_Unc)
                        if str(ScattCatalog[Sample]['Intent']).find('Empty') != -1:
                            HalfPolEmptySlices['Empty'] = vSANS_HalfPolSlices('HalfPol', Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, UScaledData, UScaledData_Unc, DScaledData, DScaledData_Unc)

                    UnpolScaledData, UnpolScaledData_Unc = AbsScale('Unpol', Sample, Config, BB_per_second, Solid_Angle, Plex, ScattCatalog, TransCatalog)
                    if 'NA' not in UnpolScaledData:
                        if YesNo_2DCombinedFiles > 0:
                            representative_filenumber = ScattCatalog[Sample]['Config(s)'][Config]['Unpol'][0]
                            Qx, Qy, Qz, Q_total, Q_perp_unc, Q_parl_unc, InPlaneAngleMap, dimXX, dimYY, Shadow_Mask = QCalculation_AllDetectors(representative_filenumber, Config)
                            QValues_All = {'QX':Qx,'QY':Qy,'QZ':Qz,'Q_total':Q_total,'Q_perp_unc':Q_perp_unc,'Q_parl_unc':Q_parl_unc}
                            ASCIIlike_Output('Unpol', Sample, Config, UnpolScaledData, UnpolScaledData_Unc, QValues_All, GeneralMaskWOSolenoid)
                        if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                            UnpolSampleSlices[Sample] = vSANS_UnpolSlices('Unpol', Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, UnpolScaledData, UnpolScaledData_Unc)
                        if str(ScattCatalog[Sample]['Intent']).find('Empty') != -1:
                            UnpolEmptySlices['Empty'] = vSANS_UnpolSlices('Unpol', Sample, Config, InPlaneAngleMap, Q_min, Q_max, Q_bins, QValues_All, GeneralMaskWSolenoid, UnpolScaledData, UnpolScaledData_Unc)


        #Catergorize Samples and Sample Bases
        FullPol_BaseToSampleMap = {}
        for Base in Sample_Bases:
            for Sample in Sample_Names:
                if str(Sample).find(Base) != -1:
                    if Sample in ScattCatalog:                
                        if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                            if Sample in FullPolSampleSlices:
                                if Base not in FullPol_BaseToSampleMap:
                                    FullPol_BaseToSampleMap[Base] = [Sample]
                                else:
                                    FullPol_BaseToSampleMap[Base].append(Sample)

        HalfPol_BaseToSampleMap = {}
        for Base in Sample_Bases:
            for Sample in Sample_Names:
                if str(Sample).find(Base) != -1:
                    if Sample in ScattCatalog:                
                        if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                            if Sample in HalfPolSampleSlices:
                                if Base not in HalfPol_BaseToSampleMap:
                                    HalfPol_BaseToSampleMap[Base] = [Sample]
                                else:
                                    HalfPol_BaseToSampleMap[Base].append(Sample)

        Unpol_BaseToSampleMap = {}
        for Base in Sample_Bases:
            for Sample in Sample_Names:
                if str(Sample).find(Base) != -1:
                    if Sample in ScattCatalog:                
                        if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                            if Sample in UnpolSampleSlices:
                                if Base not in Unpol_BaseToSampleMap:
                                    Unpol_BaseToSampleMap[Base] = [Sample]
                                else:
                                    Unpol_BaseToSampleMap[Base].append(Sample)
        print('Unpol_BaseToSampleMap')
        print(Unpol_BaseToSampleMap)
                        
        print('Saving text files and data plots...')
        FullPolResults = {}
        Representative_FullPolSample = 'NA'
        HalfPolResults = {}
        Representative_HalfPolSample = 'NA'
        UnpolResults = {}
        Representative_UnpolSample = 'NA'
        for Sample in Sample_Names:
            if Sample in ScattCatalog:                
                if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                    if Sample in FullPolSampleSlices:
                        Representative_FullPolSample = Sample
                        FullPolResults[Sample] = vSANS_ProcessFullPolSlices(FullPolSampleSlices, Sample, FullPolEmptySlices)
                    if Sample in HalfPolSampleSlices:
                        Representative_HalfPolSample = Sample
                        HalfPolResults[Sample] = vSANS_ProcessHalfPolSlices(HalfPolSampleSlices, Sample, HalfPolEmptySlices)
                    if Sample in UnpolSampleSlices:
                        Representative_UnpolSample = Sample
                        UnpolResults[Sample] = vSANS_ProcessUnpolSlices(UnpolSampleSlices, Sample, UnpolEmptySlices)
        if AutoSubtractEmpty == 0:
            if 'Empty' in FullPolEmptySlices:
                FullPolResults['Empty'] = vSANS_ProcessFullPolSlices(FullPolEmptySlices, 'Empty', FullPolEmptySlices)
            if 'Empty' in HalfPolEmptySlices:
                HalfPolResults['Empty'] = vSANS_ProcessHalfPolSlices(HalfPolEmptySlices, 'Empty', HalfPolEmptySlices)
            if 'Empty' in UnpolEmptySlices:
                UnpolResults['Empty'] = vSANS_ProcessUnpolSlices(UnpolEmptySlices, 'Empty', UnpolEmptySlices)

        '''
        CheckTypes = 0
        if ComparePolUnpolCircSums == 1:
            if str(Representative_FullPolSample).find('NA') == -1:
                CheckTypes += 1
                Q = np.array(FullPolResults[Representative_FullPolSample]['QCirc'])
                I = np.array(FullPolResults[Representative_FullPolSample]['CircSum'])
                DI = np.array(FullPolResults[Representative_FullPolSample]['CircSum_Unc'])
            if str(Representative_HalfPolSample).find('NA') == -1:
                CheckTypes += 1
                Q2 = np.array(HalfPolResults[Representative_HalfPolSample]['QCirc'])
                I2 = np.array(HalfPolResults[Representative_HalfPolSample]['CircSum'])
                DI2 = np.array(HalfPolResults[Representative_HalfPolSample]['CircSum_Unc'])
            if str(Representative_UnpolSample).find('NA') == -1:
                CheckTypes += 1
                Q3 = np.array(UnpolResults[Representative_UnpolSample]['QCirc'])
                I3 = np.array(UnpolResults[Representative_UnpolSample]['CircSum'])
                DI3 = np.array(UnpolResults[Representative_UnpolSample]['CircSum_Unc'])
            if CheckTypes >= 2:
                fig = plt.figure()
                ax = plt.axes()
                ax.set_xscale("log")
                ax.set_yscale("log")
                if str(Representative_FullPolSample).find('NA') == -1:
                    ax.errorbar(Q, I, yerr=DI, fmt = 'b*', label='FullPol Sum, {samp}'.format(samp=Representative_FullPolSample))
                if str(Representative_HalfPolSample).find('NA') == -1:
                    ax.errorbar(Q2, I2, yerr=DI2, fmt = 'r*', label='HalfPol Sum, {samp}'.format(samp=Representative_HalfPolSample))
                if str(Representative_UnpolSample).find('NA') == -1:
                    ax.errorbar(Q3, I3, yerr=DI3, fmt = 'g*', label='Unpol, {samp}'.format(samp=Representative_UnpolSample))
                plt.xlabel('Q')
                plt.ylabel('Intensity')
                plt.title('Circ sum for {cf}'.format(cf = Config))
                plt.legend()
                fig.savefig(save_path + 'CompareCircSum_PolToUnpol,{cf}.png'.format(cf = Config))
                plt.pause(2)
                plt.close()
                '''

        plot_symbols = ['b*', 'r*', 'g*', 'c*','m*', 'y*', 'k*','b-', 'r-', 'g-', 'c-','m-', 'y-', 'k-']
        symbol_max = 14

        if CompareCircSums == 1:
            for Base in Unpol_BaseToSampleMap:
                symbol_counter = 0
                HaveData = 0
                fig = plt.figure()
                ax = plt.axes()
                ax.set_xscale("log")
                ax.set_yscale("log")
                for Sample in Unpol_BaseToSampleMap[Base]:
                    if Sample in ScattCatalog:                
                        if 'Sample' in str(ScattCatalog[Sample]['Intent']):
                            if Sample in UnpolSampleSlices:
                                HaveData += 1
                                Q = np.array(UnpolResults[Sample]['QCirc'])
                                I = np.array(UnpolResults[Sample]['CircSum'])
                                DI = np.array(UnpolResults[Sample]['CircSum_Unc'])
                                symbol = str(plot_symbols[symbol_counter])
                                ax.errorbar(Q, I, yerr=DI, fmt = symbol, label='CircSum, {samp}'.format(samp=Sample))
                                symbol_counter += 1
                                if symbol_counter >= symbol_max:
                                    symbol_counter = 0
                if HaveData >= 2:
                    plt.xlabel('Q')
                    plt.ylabel('Intensity')
                    plt.title('Unpolarized sum for_{cf}'.format(cf = Config))
                    plt.legend()
                    fig.savefig(save_path + 'Compare_CircSumUnpol_{base},{cf}.png'.format(base = Base, cf = Config))
                    plt.pause(2)
                    plt.close()
                else:
                    plt.close()

        if CompareCircSums == 1:
            for Base in FullPol_BaseToSampleMap:
                symbol_counter = 0
                HaveData = 0
                fig = plt.figure()
                ax = plt.axes()
                ax.set_xscale("log")
                ax.set_yscale("log")
                for Sample in FullPol_BaseToSampleMap[Base]:
                    if Sample in ScattCatalog:                
                        #if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                        if 'Sample' in str(ScattCatalog[Sample]['Intent']):
                            if Sample in FullPolSampleSlices:
                                HaveData += 1
                                Q = np.array(FullPolResults[Sample]['QCirc'])
                                I = np.array(FullPolResults[Sample]['CircSum'])
                                DI = np.array(FullPolResults[Sample]['CircSum_Unc'])
                                symbol = str(plot_symbols[symbol_counter])
                                ax.errorbar(Q, I, yerr=DI, fmt = symbol, label='CircSum, {samp}'.format(samp=Sample))
                                symbol_counter += 1
                                if symbol_counter >= symbol_max:
                                    symbol_counter = 0
                if HaveData >= 2:
                    plt.xlabel('Q')
                    plt.ylabel('Intensity')
                    plt.title('Circular sum for_{cf}'.format(cf = Config))
                    plt.legend()
                    fig.savefig(save_path + 'Compare_CircSumFullPol_{base},{cf}.png'.format(base = Base, cf = Config))
                    plt.pause(2)
                    plt.close()
                else:
                    plt.close()
                    
        '''
        if CompareMPerpSF == 1:
            symbol_counter = 0
            fig = plt.figure()
            ax = plt.axes()
            ax.set_xscale("log")
            ax.set_yscale("log")
            for Sample in Sample_Names:
                if Sample in ScattCatalog:                
                    if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                        if Sample in FullPolSampleSlices:
                            Q = np.array(FullPolResults[Sample]['QHorzVert'])
                            I = np.array(FullPolResults[Sample]['M_Perp'])
                            DI = np.array(FullPolResults[Sample]['M_Perp_Unc'])
                            symbol = str(plot_symbols[symbol_counter])
                            ax.errorbar(Q, I, yerr=DI, fmt = symbol, label='M_Perp, {samp}'.format(samp=Sample))
                            symbol_counter += 1
                            if symbol_counter >= symbol_max:
                                symbol_counter = 0
            plt.xlabel('Q')
            plt.ylabel('Intensity')
            plt.title('M_Perp for_{cf}'.format(cf = Config))
            plt.legend()
            fig.savefig(save_path + 'Compare_MPerp_{cf}.png'.format(cf = Config))
            plt.pause(2)
            plt.close()

        if CompareMParlNSF == 1:
            symbol_counter = 0
            fig = plt.figure()
            ax = plt.axes()
            ax.set_xscale("log")
            ax.set_yscale("log")
            for Sample in Sample_Names:
                if Sample in ScattCatalog:                
                    if str(ScattCatalog[Sample]['Intent']).find('Sample') != -1:
                        if Sample in FullPolSampleSlices:
                            Q = np.array(FullPolResults[Sample]['QHorzVert'])
                            I = np.array(FullPolResults[Sample]['M_Parl_NSF'])
                            DI = np.array(FullPolResults[Sample]['M_Parl_NSF_Unc'])
                            symbol = str(plot_symbols[symbol_counter])
                            ax.errorbar(Q, I, yerr=DI, fmt = symbol, label='M_Parl_NSF (division), {samp}'.format(samp=Sample))
                            symbol_counter += 1
                            if symbol_counter >= symbol_max:
                                symbol_counter = 0
            plt.xlabel('Q')
            plt.ylabel('Intensity')
            plt.title('M_Parl_NSF,Div for_{cf}'.format(cf = Config))
            plt.legend()
            fig.savefig(save_path + 'Compare_MParl_NSF_{cf}.png'.format(cf = Config))
            plt.pause(2)
            plt.close()
            '''
                            

#*************************************************
#***           End of 'The Program'            ***
#*************************************************



