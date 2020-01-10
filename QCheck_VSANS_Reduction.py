import numpy as np
import h5py
import scipy as sp
from scipy.optimize.minpack import curve_fit
import matplotlib.pyplot as plt
from pathlib import Path
import dateutil
import datetime
from numpy.linalg import inv
from uncertainties import unumpy
import os

#The following is from Fe3O4Cal_Nov2019.py:
path = ''
TransPanel = 'MR' #Default is 'MR'
SectorCutAngles = 15.0
UsePolCorr = 1
PlotYesNo = 1 #1 means yes
#SubtractEmptyIfAvailable = 1
YesNoManualHe3Entry = 0 #0 for no (default), 1 for yes
New_HE3_Files = {}
MuValues = {} #[3.374, 3.105]=[Fras, Bur]; should not be needed after July 2019
TeValues = {} #[0.86, 0.86]=[Fras, Bur]; should not be needed after July 2019

'''
This program is set to reduce VSANS data using middle and front detectors - umnpol, fullpol available.
To do: BS shadow, deadtime corr., check abs. scaling, uncertainty propagation through , choice of 2 cross-section empty files, half-pol
'''

#*************************************************
#***        Definitions, Functions             ***
#*************************************************

short_detectors = ["MT", "MB", "ML", "MR", "FT", "FB", "FL", "FR"]
middle_detectors = ["MT", "MB", "ML", "MR"]
sector_slices = ["Left", "Right"] #["Horz", "Vert", "Diag"]

def Unique_Config_ID(filenumber):
    
    filename = path + "sans" + str(filenumber) + ".nxs.ngv"
    config = Path(filename)
    if config.is_file():
        f = h5py.File(filename)
        Desired_FrontCarriage_Distance = int(f['entry/DAS_logs/carriage1Trans/desiredSoftPosition'][0]) #in cm
        Desired_MiddleCarriage_Distance = int(f['entry/DAS_logs/carriage2Trans/desiredSoftPosition'][0]) #in cm
        Wavelength = f['entry/DAS_logs/wavelength/wavelength'][0]
        Guides = int(f['entry/DAS_logs/guide/guide'][0])
        Configuration_ID = str(Guides) + "Gd" + str(Desired_FrontCarriage_Distance) + "cmF" + str(Desired_MiddleCarriage_Distance) + "cmM" + str(Wavelength) + "Ang"
        
    return Configuration_ID

def File_Type(filenumber):

    Type = 'UNKNOWN'
    SolenoidPosition = 'UNKNOWN'
    
    filename = path + "sans" + str(filenumber) + ".nxs.ngv"
    config = Path(filename)
    if config.is_file():
        f = h5py.File(filename)
        Purpose = f['entry/reduction/file_purpose'][()] #SCATT, TRANS, HE3
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

def SortDataAutomatic(YesNoManualHe3Entry, New_HE3_Files, MuValues, TeValues):

    BlockBeam = {}
    Configs = {}
    Sample_Names = {}
    Scatt = {}
    Trans = {}
    Pol_Trans = {}
    HE3_Trans = {}

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
    
    filelist = [fn for fn in os.listdir("./") if fn.endswith(".nxs.ngv")] #or filenames = [fn for fn in os.listdir("./") if os.path.isfile(fn)]
    if len(filelist) >= 1:
        for name in filelist:
            filename = str(name)
            filenumber = int(filename[4:9])
            if start_number == 0:
                start_number = filenumber
            config = Path(filename)
            if config.is_file():
                f = h5py.File(filename)
                Count_time = f['entry/collection_time'][0]
                Descrip = str(f['entry/sample/description'][0])
                Descrip = Descrip[2:]
                Descrip = Descrip[:-1]
                print('Reading:', filenumber, ' ', Descrip)
                if Count_time > 59 and str(Descrip).find("Align") == -1:

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
                    Not_Sample = [DT5, DT4, DT3, DT2, DT1, V5, V4, V3, V2, V1]
                    for i in Not_Sample:
                        Sample_Name = Sample_Name.replace(i, '')
                    Sample_Name = Sample_Name.replace(' ', '')
                    Sample_Base = Sample_Name
                    Sample_Name = Sample_Name + '_' + str(Voltage) + 'V_' + str(Desired_Temp) + 'K'

                    Purpose = f['entry/reduction/file_purpose'][()] #SCATT, TRANS, HE3
                    Intent = f['entry/reduction/intent'][()] #Sample, Empty, Blocked Beam, Open Beam
                    #ID = str(f['entry/sample/group_id'][0])
                    End_time = dateutil.parser.parse(f['entry/end_time'][0])
                    TimeOfMeasurement = (End_time.timestamp() - Count_time/2)/3600.0 #in hours
                    Trans_Counts = f['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    #trans_mask = Trans_masks['MR']
                    #trans_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    #trans_data = trans_data*trans_mask
                    #Trans_Counts = trans_data.sum()
                    MonCounts = f['entry/control/monitor_counts'][0]
                    Trans_Distance = f['entry/instrument/detector_{ds}/distance'.format(ds=TransPanel)][0]
                    Attenuation = f['entry/DAS_logs/attenuator/attenuator'][0]
                    Wavelength = f['entry/DAS_logs/wavelength/wavelength'][0]
                    Config = Unique_Config_ID(filenumber)
                    FrontPolDirection = f['entry/DAS_logs/frontPolarization/direction'][()]
                    if "backPolarization" in f['entry/DAS_logs/']:
                        BackPolDirection = f['entry/DAS_logs/backPolarization/direction'][()]
                    else:
                        BackPolDirection = [b'UNPOLARIZED']
                    if len(Configs) < 1:
                        Configs = {Config : filenumber}
                    else:
                        if Config not in Configs:
                            Configs.append({Config : filenumber})

                    
                    if str(Intent).find("Blocked") != -1: #i.e. a blocked beam
                        if Config not in BlockBeam:
                             BlockBeam[Config] = {'Scatt':{'File' : 'NA'}, 'Trans':{'File' : 'NA', 'CountsPerSecond' : 'NA'}}
                             
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
                                
                        Intent_short = str(Intent)
                        Intent_short = Intent_short[3:-2]
                        Intent_short = Intent_short.replace(' Cell', '')
                        Intent_short = Intent_short.replace(' Beam', '')
                            

                        
                        if str(Purpose).find("SCATT") != -1:
                            if Sample_Name not in Scatt:
                                Scatt[Sample_Name] = {'Intent': Intent_short, 'Sample_Base': Sample_Base, 'Config(s)' : {Config : {'Unpol': 'NA', 'U' : 'NA', 'D' : 'NA','UU' : 'NA', 'DU' : 'NA', 'DD' : 'NA', 'UD' : 'NA', 'UU_Time' : 'NA', 'DU_Time' : 'NA', 'DD_Time' : 'NA', 'UD_Time' : 'NA'}}}
                            if Config not in Scatt[Sample_Name]['Config(s)']:
                                #Check that multipe configurations per sample are processed properly; Scatt[Sample_Name]['Config(s)'].append(Config)
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
                            else: #i.e. automatic entry
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
                                        else:
                                            HE3_Trans[CellTimeIdentifier]['Config'].append(HE3IN_config)
                                            HE3_Trans[CellTimeIdentifier]['HE3_OUT_file'].append(HE3OUT_filenumber)
                                            HE3_Trans[CellTimeIdentifier]['HE3_IN_file'].append(HE3IN_filenumber)
                                            HE3_Trans[CellTimeIdentifier]['Elasped_time'].append(Elasped_time)
                                            



    return Sample_Names, Configs, BlockBeam, Scatt, Trans, Pol_Trans, HE3_Trans

def ReadIn_Masks():

    Masks = {}
    single_mask = {}

    filename = '0'
    Mask_files = [fn for fn in os.listdir("./") if fn.endswith("MASK.h5")]
    if len(Mask_files) >= 1:
        for name in Mask_files:
            filename = str(name)
            associated_filenumber = filename[:5]
            if associated_filenumber.isdigit() == True:
                ConfigID = Unique_Config_ID(associated_filenumber)
                if ConfigID not in Masks:
                    Masks[ConfigID] = {'Trans' : 'NA', 'Scatt_Standard' : 'NA', 'Scatt_WithSolenoid' : 'NA'}
                Type, SolenoidPosition = File_Type(associated_filenumber)
                config = Path(filename)
                if config.is_file():
                    f = h5py.File(filename)
                    for dshort in short_detectors:
                        mask_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                        '''
                        This reverses zeros and ones (assuming IGOR-made masks) so that zeros become the pixels to ignore:
                        '''
                        single_mask[dshort] = np.zeros_like(mask_data)
                        single_mask[dshort][mask_data == 0] = 1.0
                        
                    if str(Type).find("TRANS") != -1:
                        Masks[ConfigID]['Trans'] = single_mask.copy()
                        print('Saved', filename, ' as Trans Mask for', ConfigID)
                        
                    if str(Type).find("SCATT") != -1 and str(SolenoidPosition).find("OUT") != -1:
                        Masks[ConfigID]['Scatt_Standard'] = single_mask.copy()
                        print('Saved', filename, ' as Standard Scatt Mask for', ConfigID)
                        
                    if str(Type).find("SCATT") != -1 and str(SolenoidPosition).find("IN") != -1:
                        Masks[ConfigID]['Scatt_WithSolenoid'] = single_mask.copy()
                        print('Saved', filename, ' as Scatt Mask With Solenoid for', ConfigID)
                        
                
    return Masks

def Process_Transmissions(BlockBeam, Masks, HE3_Trans, Pol_Trans, Trans):

    for Cell in HE3_Trans:
        if 'Elasped_time' in HE3_Trans[Cell]:
            counter = 0
            for InFile in HE3_Trans[Cell]['HE3_IN_file']:
                OutFile = HE3_Trans[Cell]['HE3_OUT_file'][counter]
                Config = HE3_Trans[Cell]['Config'][counter]
                if Config in BlockBeam:
                    if 'NA' not in BlockBeam[Config]['Trans']['File']:
                        BBFile = BlockBeam[Config]['Trans']['File'][0]
                    elif 'NA' not in BlockBeam[Config]['Scatt']['File']:
                        BBFile = BlockBeam[Config]['Scatt']['File'][0]
                    else:
                        BBFile = 0
                if Config in Masks and 'NA' not in Masks[Config]['Trans']:
                    mask_it = np.array(Masks[Config]['Trans'][TransPanel])
                    IN = path + "sans" + str(InFile) + ".nxs.ngv"
                    OUT = path + "sans" + str(OutFile) + ".nxs.ngv"
                    f = h5py.File(IN)
                    INMon = f['entry/control/monitor_counts'][0]
                    IN_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    INCount_time = f['entry/collection_time'][0]
                    g = h5py.File(OUT)
                    OUTMon = g['entry/control/monitor_counts'][0]
                    OUT_data = np.array(g['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    OUTCount_time = g['entry/collection_time'][0]
                    if BBFile == 0:
                        BB_Data = np.zeros_like(IN_data)
                        BBCount_time = 1.0  
                    else:
                        BB = path + "sans" + str(BBFile) + ".nxs.ngv"
                        h = h5py.File(BB)
                        BBCount_time = h['entry/collection_time'][0]
                        BB_data = np.array(h['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    trans_num = (IN_data - BB_data*(INCount_time/BBCount_time))*mask_it
                    trans_denom = (OUT_data - BB_data*(OUTCount_time/BBCount_time))*mask_it
                    trans = (np.sum(trans_num)/np.sum(trans_denom))*(OUTMon / INMon)
                    if 'Transmission' not in HE3_Trans[Cell]:
                        HE3_Trans[Cell]['Transmission'] = [trans]
                    else:
                        HE3_Trans[Cell]['Transmission'].append(trans)
                else: #no mask for HE3_Trans
                    IN = path + "sans" + str(InFile) + ".nxs.ngv"
                    OUT = path + "sans" + str(OutFile) + ".nxs.ngv"
                    f = h5py.File(IN)
                    INMon = f['entry/control/monitor_counts'][0]
                    IN_counts = f['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    INCount_time = f['entry/collection_time'][0]
                    g = h5py.File(OUT)
                    OUTMon = g['entry/control/monitor_counts'][0]
                    OUT_counts = g['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    OUTCount_time = g['entry/collection_time'][0]
                    if BBFile == 0:
                        BB_counts = 0.0
                        BBCount_time = 1.0
                    else:
                        BB = path + "sans" + str(BBFile) + ".nxs.ngv"
                        h = h5py.File(BB)
                        BBCount_time = h['entry/collection_time'][0]
                        BB_counts = h['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    trans_num = (IN_counts - BB_counts*(INCount_time/BBCount_time))
                    trans_denom = (OUT_counts - BB_counts*(OUTCount_time/BBCount_time))
                    trans = (trans_num/trans_denom)*(OUTMon / INMon)
                    if 'Transmission' not in HE3_Trans[Cell]:
                        HE3_Trans[Cell]['Transmission'] = [trans]
                    else:
                        HE3_Trans[Cell]['Transmission'].append(trans)                
                counter += 1

    for Samp in Pol_Trans:
        if 'NA' not in Pol_Trans[Samp]['T_UU']['File']:
            counter = 0
            for UUFile in Pol_Trans[Samp]['T_UU']['File']:
                DUFile = Pol_Trans[Samp]['T_DU']['File'][counter]
                DDFile = Pol_Trans[Samp]['T_DD']['File'][counter]
                UDFile = Pol_Trans[Samp]['T_UD']['File'][counter]
                SMFile = Pol_Trans[Samp]['T_SM']['File'][counter]
                Config = Pol_Trans[Samp]['Config'][counter]
                if Config in BlockBeam:
                    if 'NA' not in BlockBeam[Config]['Trans']['File']:
                        BBFile = BlockBeam[Config]['Trans']['File'][0]
                    elif 'NA' not in BlockBeam[Config]['Scatt']['File']:
                        BBFile = BlockBeam[Config]['Scatt']['File'][0]
                    else:
                        BBFile = 0
                if Config in Masks and 'NA' not in Masks[Config]['Trans']:
                    mask_it = np.array(Masks[Config]['Trans'][TransPanel])
                    UU = path + "sans" + str(UUFile) + ".nxs.ngv"
                    DU = path + "sans" + str(DUFile) + ".nxs.ngv"
                    DD = path + "sans" + str(DDFile) + ".nxs.ngv"
                    UD = path + "sans" + str(UDFile) + ".nxs.ngv"
                    SM = path + "sans" + str(SMFile) + ".nxs.ngv"
                    f = h5py.File(UU)
                    UUMon = f['entry/control/monitor_counts'][0]
                    UU_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    UUCount_time = f['entry/collection_time'][0]
                    g = h5py.File(DU)
                    DUMon = g['entry/control/monitor_counts'][0]
                    DU_data = np.array(g['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    DUCount_time = g['entry/collection_time'][0]
                    h = h5py.File(DD)
                    DDMon = h['entry/control/monitor_counts'][0]
                    DD_data = np.array(h['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    DDCount_time = h['entry/collection_time'][0]
                    j = h5py.File(UD)
                    UDMon = j['entry/control/monitor_counts'][0]
                    UD_data = np.array(j['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    UDCount_time = j['entry/collection_time'][0]
                    k = h5py.File(SM)
                    SMMon = k['entry/control/monitor_counts'][0]
                    SM_data = np.array(k['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    SMCount_time = k['entry/collection_time'][0]
                    if BBFile == 0:
                        BB_Data = np.zeros_like(UU_data)
                        BBCount_time = 1.0
                    else:
                        BB = path + "sans" + str(BBFile) + ".nxs.ngv"
                        l = h5py.File(BB)
                        BBMon = l['entry/control/monitor_counts'][0]
                        BBCount_time = l['entry/collection_time'][0]
                        BB_data = np.array(l['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    trans_UU = (UU_data - BB_data*(UUCount_time/BBCount_time))*mask_it
                    trans_DU = (DU_data - BB_data*(DUCount_time/BBCount_time))*mask_it
                    trans_DD = (DD_data - BB_data*(DDCount_time/BBCount_time))*mask_it
                    trans_UD = (UD_data - BB_data*(UDCount_time/BBCount_time))*mask_it
                    trans_SM = (SM_data - BB_data*(SMCount_time/SMCount_time))*mask_it
                    UU_value = (np.sum(trans_UU)/np.sum(trans_SM))*(SMMon / UUMon)
                    UD_value = (np.sum(trans_UD)/np.sum(trans_SM))*(SMMon / UDMon)
                    DD_value = (np.sum(trans_DD)/np.sum(trans_SM))*(SMMon / DDMon)
                    DU_value = (np.sum(trans_DU)/np.sum(trans_SM))*(SMMon / DUMon)
                    SM_value = np.sum(trans_SM*1E8/SMMon)
                    if 'Trans' not in Pol_Trans[Samp]['T_UU']:
                        Pol_Trans[Samp]['T_UU']['Trans'] = [UU_value]
                        Pol_Trans[Samp]['T_DU']['Trans'] = [DU_value]
                        Pol_Trans[Samp]['T_DD']['Trans'] = [DD_value]
                        Pol_Trans[Samp]['T_UD']['Trans'] = [UD_value]
                        Pol_Trans[Samp]['T_SM']['Trans_Cts'] = [SM_value]
                    else:
                        Pol_Trans[Samp]['T_UU']['Trans'].append(UU_value)
                        Pol_Trans[Samp]['T_DU']['Trans'].append(DU_value)
                        Pol_Trans[Samp]['T_DD']['Trans'].append(DD_value)
                        Pol_Trans[Samp]['T_UD']['Trans'].append(UD_value)
                        Pol_Trans[Samp]['T_SM']['Trans_Cts'].append(SM_value)
                else: #no mask for Full_Pol trans
                    UU = path + "sans" + str(UUFile) + ".nxs.ngv"
                    DU = path + "sans" + str(DUFile) + ".nxs.ngv"
                    DD = path + "sans" + str(DDFile) + ".nxs.ngv"
                    UD = path + "sans" + str(UDFile) + ".nxs.ngv"
                    SM = path + "sans" + str(SMFile) + ".nxs.ngv"
                    f = h5py.File(UU)
                    UUMon = f['entry/control/monitor_counts'][0]
                    UU_counts = f['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    UUCount_time = f['entry/collection_time'][0]
                    g = h5py.File(DU)
                    DUMon = g['entry/control/monitor_counts'][0]
                    DU_counts = g['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    DUCount_time = g['entry/collection_time'][0]
                    h = h5py.File(DD)
                    DDMon = h['entry/control/monitor_counts'][0]
                    DD_counts = h['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    DDCount_time = h['entry/collection_time'][0]
                    j = h5py.File(UD)
                    UDMon = j['entry/control/monitor_counts'][0]
                    UD_counts = j['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    UDCount_time = j['entry/collection_time'][0]
                    k = h5py.File(SM)
                    SMMon = k['entry/control/monitor_counts'][0]
                    SM_counts = k['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    SMCount_time = k['entry/collection_time'][0]
                    if BBFile == 0:
                        BB_counts = 0.0
                        BBCount_time = 1.0
                    else:
                        BB = path + "sans" + str(BBFile) + ".nxs.ngv"
                        l = h5py.File(BB)
                        BBCount_time = l['entry/collection_time'][0]
                        BB_counts = l['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    trans_UU = (UU_counts - BB_counts*(UUCount_time/BBCount_time))
                    trans_DU = (DU_counts - BB_counts*(DUCount_time/BBCount_time))
                    trans_DD = (DD_counts - BB_counts*(DDCount_time/BBCount_time))
                    trans_UD = (UD_counts - BB_counts*(UDCount_time/BBCount_time))
                    trans_SM = (SM_counts - BB_counts*(SMCount_time/BBCount_time))
                    UU_value = (trans_UU/trans_SM)*(SMMon / UUMon)
                    UD_value = (trans_DU/trans_SM)*(SMMon / UDMon)
                    DD_value = (trans_DD/trans_SM)*(SMMon / DDMon)
                    DU_value = (trans_UD/trans_SM)*(SMMon / DUMon)
                    SM_value = trans_SM*1E8/SMMon
                    if 'Trans' not in Pol_Trans[Samp]['T_UU']:
                        Pol_Trans[Samp]['T_UU']['Trans'] = [UU_value]
                        Pol_Trans[Samp]['T_DU']['Trans'] = [DU_value]
                        Pol_Trans[Samp]['T_DD']['Trans'] = [DD_value]
                        Pol_Trans[Samp]['T_UD']['Trans'] = [UD_value]
                        Pol_Trans[Samp]['T_SM']['Trans_Cts'] = [SM_value]
                    else:
                        Pol_Trans[Samp]['T_UU']['Trans'].append(UU_value)
                        Pol_Trans[Samp]['T_DU']['Trans'].append(DU_value)
                        Pol_Trans[Samp]['T_DD']['Trans'].append(DD_value)
                        Pol_Trans[Samp]['T_UD']['Trans'].append(UD_value)
                        Pol_Trans[Samp]['T_SM']['Trans_Cts'].append(SM_value)
                counter += 1

    for Samp in Trans:
        for Config in Trans[Samp]['Config(s)']:
            if Config in BlockBeam:
                if 'NA' not in BlockBeam[Config]['Trans']['File']:
                    BBFile = BlockBeam[Config]['Trans']['File'][0]
                elif 'NA' not in BlockBeam[Config]['Scatt']['File']:
                    BBFile = BlockBeam[Config]['Scatt']['File'][0]
                else:
                    BBFile = 0
                if Config in Masks and 'NA' not in Masks[Config]['Trans']:
                    mask_it = np.array(Masks[Config]['Trans'][TransPanel])
                    if BBFile == 0:
                        example_file = Configs[Config]
                        BB = path + "sans" + str(example_file) + ".nxs.ngv"
                        l = h5py.File(BB)
                        Example_data = np.array(l['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                        BB_Data = np.zeros_like(Example_data)
                        BBCount_time = 1.0
                    else:
                        BB = path + "sans" + str(BBFile) + ".nxs.ngv"
                        l = h5py.File(BB)
                        BBMon = l['entry/control/monitor_counts'][0]
                        BBCount_time = l['entry/collection_time'][0]
                        BB_data = np.array(l['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                    if 'NA' not in Trans[Samp]['Config(s)'][Config]['Unpol_Files']:
                        for UNF in Trans[Samp]['Config(s)'][Config]['Unpol_Files']:
                            UN_file = path + "sans" + str(UNF) + ".nxs.ngv"
                            f = h5py.File(UN_file)
                            UNMon = f['entry/control/monitor_counts'][0]
                            UN_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                            UNCount_time = f['entry/collection_time'][0]
                            UNTrans = (UN_data - BB_data*(UNCount_time/BBCount_time))*mask_it
                            UN_Trans = np.sum(UNTrans)*1E8/UNMon
                            if 'NA' in Trans[Samp]['Config(s)'][Config]['Unpol_Trans_Cts']:
                                Trans[Samp]['Config(s)'][Config]['Unpol_Trans_Cts'] = [UN_Trans]
                            else:
                                Trans[Samp]['Config(s)'][Config]['Unpol_Trans_Cts'].append(UN_Trans)        
                    if 'NA' not in Trans[Samp]['Config(s)'][Config]['U_Files']:
                        for UF in Trans[Samp]['Config(s)'][Config]['U_Files']:
                            U_file = path + "sans" + str(UF) + ".nxs.ngv"
                            f = h5py.File(U_file)
                            UMon = f['entry/control/monitor_counts'][0]
                            U_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                            UCount_time = f['entry/collection_time'][0]
                            UTrans = (U_data - BB_data*(UCount_time/BBCount_time))*mask_it
                            U_Trans = np.sum(UTrans)*1E8/UNMon
                            if 'NA' in Trans[Samp]['Config(s)'][Config]['U_Trans_Cts']:
                                Trans[Samp]['Config(s)'][Config]['U_Trans_Cts'] = [U_Trans]
                            else:
                                Trans[Samp]['Config(s)'][Config]['U_Trans_Cts'].append(U_Trans)
                else: #no mask for Trans
                    if BBFile == 0:
                        BB_counts = 0.0
                        BBCount_time = 1.0
                    else:
                        BB = path + "sans" + str(BBFile) + ".nxs.ngv"
                        l = h5py.File(BB)
                        BBCount_time = l['entry/collection_time'][0]
                        BB_counts = l['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                    if 'NA' not in Trans[Samp]['Config(s)'][Config]['Unpol_Files']:
                        for UNF in Trans[Samp]['Config(s)'][Config]['Unpol_Files']:
                            UN_file = path + "sans" + str(UNF) + ".nxs.ngv"
                            f = h5py.File(UN_file)
                            UNMon = f['entry/control/monitor_counts'][0]
                            UN_counts = f['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                            UNCount_time = f['entry/collection_time'][0]
                            UNTrans = (UN_counts - BB_counts*(UNCount_time/BBCount_time))
                            UN_Trans = UNTrans * 1E8 / UNMon
                            if 'NA' in Trans[Samp]['Config(s)'][Config]['Unpol_Trans_Cts']:
                                Trans[Samp]['Config(s)'][Config]['Unpol_Trans_Cts'] = [UN_Trans]
                            else:
                                Trans[Samp]['Config(s)'][Config]['Unpol_Trans_Cts'].append(UN_Trans)
                    if 'NA' not in Trans[Samp]['Config(s)'][Config]['U_Files']:
                        for UF in Trans[Samp]['Config(s)'][Config]['U_Files']:
                            U_file = path + "sans" + str(UF) + ".nxs.ngv"
                            f = h5py.File(U_file)
                            UMon = f['entry/control/monitor_counts'][0]
                            U_counts = f['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                            UCount_time = f['entry/collection_time'][0]
                            UTrans = (U_counts - BB_counts*(UCount_time/BBCount_time))
                            U_Trans = UTrans * 1E8 / UMon
                            if 'NA' in Trans[Samp]['Config(s)'][Config]['U_Trans_Cts']:
                                Trans[Samp]['Config(s)'][Config]['U_Trans_Cts'] = [U_Trans]
                            else:
                                Trans[Samp]['Config(s)'][Config]['U_Trans_Cts'].append(U_Trans)
                                         
    return

def Process_ScattFiles():

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
                    
    return


def Plex_File():

    PlexData = {}

    filename = '0'
    Plex_file = [fn for fn in os.listdir("./") if fn.startswith("PLEX")]
    if len(Plex_file) >= 1:
        filename = str(Plex_file[0])
    #filename = path + "PLEX_" + str(filenumber) + "_VSANS_DIV.h5"
    config = Path(filename)
    if config.is_file():
        print('Reading in ', filename)
        f = h5py.File(filename)
        for dshort in short_detectors:
            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
            PlexData[dshort] = data.flatten()
    else:
        filenumber = start_number
        filename = path + "sans" + str(filenumber) + ".nxs.ngv"
        config = Path(filename)
        if config.is_file():
            f = h5py.File(filename)
            for dshort in short_detectors:
                data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                data_zeros = np.ones_like(data)
                PlexData[dshort] = data_zeros.flatten()
        print('Plex file not found; populated with ones instead')   
            
    return PlexData

def BlockedBeamScattCountsPerSecond(Config, representative_filenumber):

    BB_per_second = {}

    if Config in BlockBeam:
        if 'NA' not in BlockBeam[Config]['Trans']['File']:
            BBFile = BlockBeam[Config]['Trans']['File'][0]
            BB = path + "sans" + str(BBFile) + ".nxs.ngv"
            filename = str(BB)
            config = Path(filename)
            if config.is_file():
                f = h5py.File(filename)
                Count_time = f['entry/collection_time'][0]
                for dshort in short_detectors:
                    bb_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                    BB_per_second[dshort] = bb_data / Count_time
                print('Trans BB', BBFile)
        elif 'NA' not in BlockBeam[Config]['Scatt']['File']:
            BBFile = BlockBeam[Config]['Scatt']['File'][0]
            BB = path + "sans" + str(BBFile) + ".nxs.ngv"
            filename = str(BB)
            config = Path(filename)
            if config.is_file():
                f = h5py.File(filename)
                Count_time = f['entry/collection_time'][0]
                for dshort in short_detectors:
                    bb_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                    BB_per_second[dshort] = bb_data / Count_time
                print('Scatt BB', BBFile)
        else:
            BB = path + "sans" + str(representative_filenumber) + ".nxs.ngv"
            filename = str(BB)
            config = Path(filename)
            if config.is_file():
                f = h5py.File(filename)
                for dshort in short_detectors:
                    bb_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                    zero_data = np.zeros_like(bb_data)
                    BB_per_second[dshort] = zero_data
            print('No BB')
    else:
        BB = path + "sans" + str(representative_filenumber) + ".nxs.ngv"
        filename = str(BB)
        config = Path(filename)
        if config.is_file():
            f = h5py.File(filename)
            for dshort in short_detectors:
                bb_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                zero_data = np.zeros_like(bb_data)
                BB_per_second[dshort] = zero_data
        print('No BB')    

    return BB_per_second

def BlockedBeam_Averaged(BlockedBeamFiles, MeasMasks, Trans_masks):

    BlockBeam_Trans = {}
    BlockBeam_ScattPerPixel = {}
    masks = {}

    for filenumber in BlockedBeamFiles:
        filename = path + "sans" + str(filenumber) + ".nxs.ngv"
        config = Path(filename)
        if config.is_file():
            print('Reading in block beam file number:', filenumber)
            f = h5py.File(filename)
            Config_ID = Unique_Config_ID(filenumber) #int(f['entry/DAS_logs/carriage2Trans/desiredSoftPosition'][0]) #int(f['entry/instrument/detector_{ds}/distance'.format(ds=TransPanel)][0])

            Purpose = f['entry/reduction/file_purpose'][()]
            Count_time = f['entry/collection_time'][0]
            if str(Purpose).find("TRANS") != -1 or str(Purpose).find("HE3") != -1:
                
                #Trans_Counts = f['entry/instrument/detector_{ds}/integrated_count'.format(ds=TransPanel)][0]
                
                trans_mask = Trans_masks['MR']
                trans_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
                trans_data = trans_data*trans_mask
                Trans_Counts = trans_data.sum()
                
                BlockBeam_Trans[Config_ID] = {'File' : filenumber,
                                                             'CountsPerSecond' : Trans_Counts/Count_time}
            #if str(Purpose).find("SCATT") != -1:
            if str(Purpose).find("TRANS") != -1 or str(Purpose).find("HE3") != -1:
                print('BB scattering number is ', filenumber)
                BlockBeam_ScattPerPixel[Config_ID] = {'File' : filenumber}
                for dshort in short_detectors:
                    Holder = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                    if Config_ID in MeasMasks:
                        masks = MeasMasks[Config_ID]
                    else:
                        masks[dshort] = np.ones_like(Holder)
                    Sum = np.sum(Holder[masks[dshort] > 0])
                    Pixels = np.sum(masks[dshort])
                    Unc = np.sqrt(Sum)/Pixels
                    Ave = np.average(Holder[masks[dshort] > 0])
                    
                    BlockBeam_ScattPerPixel[Config_ID][dshort] = {'AvePerSec' : Ave/Count_time, 'Unc' : Unc/Count_time}
                
    return BlockBeam_Trans, BlockBeam_ScattPerPixel

def SolidAngle_AllDetectors(representative_filenumber):
    Solid_Angle = {}
    filename = path + "sans" + str(representative_filenumber) + ".nxs.ngv"
    config = Path(filename)
    if config.is_file():
        f = h5py.File(filename)
        for dshort in short_detectors:
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
            
def QCalculationAndMasks_AllDetectors(representative_filenumber, AngleWidth):

    BeamStopShadow = {}
    Mask_Right = {}
    Mask_Left = {}
    Mask_Top = {}
    Mask_Bottom = {}
    Mask_DiagonalCW = {}
    Mask_DiagonalCCW = {}
    Mask_None = {}
    Mask_User_Defined = {}
    Q_total = {}
    deltaQ = {}
    Qx = {}
    Qy = {}
    Qz = {}
    Q_perp_unc = {}
    Q_parl_unc = {}
    dimXX = {}
    dimYY = {}

    #Kludge:
    beamcenter_x_offset_KK = 0.0
    beamcenter_y_offset_KK = 0.0

    filename = path + "sans" + str(representative_filenumber) + ".nxs.ngv"
    config = Path(filename)
    if config.is_file():
        f = h5py.File(filename)
        for dshort in short_detectors:
            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
            Wavelength = f['entry/instrument/beam/monochromator/wavelength'][0]
            Wavelength_spread = f['entry/instrument/beam/monochromator/wavelength_spread'][0]
            dimX = f['entry/instrument/detector_{ds}/pixel_num_x'.format(ds=dshort)][0]
            dimY = f['entry/instrument/detector_{ds}/pixel_num_y'.format(ds=dshort)][0]
            dimXX[dshort] = f['entry/instrument/detector_{ds}/pixel_num_x'.format(ds=dshort)][0]
            dimYY[dshort] = f['entry/instrument/detector_{ds}/pixel_num_y'.format(ds=dshort)][0]
            beam_center_x = f['entry/instrument/detector_{ds}/beam_center_x'.format(ds=dshort)][0] + beamcenter_x_offset_KK
            beam_center_y = f['entry/instrument/detector_{ds}/beam_center_y'.format(ds=dshort)][0] + beamcenter_y_offset_KK
            beamstop_diameter = f['/entry/DAS_logs/C2BeamStop/diameter'][0]/10.0 #beam stop in cm; sits right in front of middle detector?
            detector_distance = f['entry/instrument/detector_{ds}/distance'.format(ds=dshort)][0]
            x_pixel_size = f['entry/instrument/detector_{ds}/x_pixel_size'.format(ds=dshort)][0]/10.0
            y_pixel_size = f['entry/instrument/detector_{ds}/y_pixel_size'.format(ds=dshort)][0]/10.0
            panel_gap = f['entry/instrument/detector_{ds}/panel_gap'.format(ds=dshort)][0]/10.0
            coeffs = f['entry/instrument/detector_{ds}/spatial_calibration'.format(ds=dshort)][0][0]/10.0
            SampleApInternal = f['/entry/DAS_logs/geometry/internalSampleApertureHeight'][0] #internal sample aperture in cm
            SampleApExternal = f['/entry/DAS_logs/geometry/externalSampleApertureHeight'][0] #external sample aperture in cm
            SourceAp = f['/entry/DAS_logs/geometry/sourceApertureHeight'][0] #source aperture in cm, assumes circular aperture(?) #0.75, 1.5, or 3 for guides; otherwise 6 cm for >= 1 guides
            FrontDetToGateValve = f['/entry/DAS_logs/carriage/frontTrans'][0] #400
            MiddleDetToGateValve = f['/entry/DAS_logs/carriage/middleTrans'][0] #1650
            #GateValveToSample = f['/entry/DAS_logs/geometry/samplePositionOffset'][0] #e.g. 91.4; gate valve to sample in cm ("Hand-measured distance from the center of the table the sample is mounted on to the sample. A positive value means the sample is offset towards the guides.")
            FrontDetToSample = f['/entry/DAS_logs/geometry/sampleToFrontLeftDetector'][0] #491.4
            MiddleDetToSample = f['/entry/DAS_logs/geometry/sampleToMiddleLeftDetector'][0] #1741.4
            #SampleToSampleAp = f['/entry/DAS_logs/geometry/SampleApertureOffset'][0] #e.g. 106.9; sample to sample aperture in cm ("Hand-measured distance between the Sample aperture and the sample.")            
            SampleToSourceAp = f['/entry/DAS_logs/geometry/sourceApertureToSample'][0] #1490.6; "Calculated distance between sample and source aperture" in cm
            #SampleApToSourceAp = f['/entry/DAS_logs/geometry/sourceApertureToSampleAperture'][0] #1383.7; "Calculated distance between sample aperture and source aperture" in cm
            #Note gate valve to source aperture distances are based on the number of guides used:
            #0=2441; 1=2157; 2=1976; 3=1782; 4=1582; 5=1381; 6=1181; 7=980; 8=780; 9=579 in form of # guides=distance in cm

            if dshort == 'MT' or dshort == 'MB' or dshort == 'FT' or dshort == 'FB':
                setback = f['entry/instrument/detector_{ds}/setback'.format(ds=dshort)][0]
                vertical_offset = f['entry/instrument/detector_{ds}/vertical_offset'.format(ds=dshort)][0]
                lateral_offset = 0
            else:
                setback = 0
                vertical_offset = 0
                lateral_offset = f['entry/instrument/detector_{ds}/lateral_offset'.format(ds=dshort)][0]

            realDistZ = detector_distance + setback

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
            BSS = np.ones_like(data)
            x0_pos =  realDistX - beam_center_x + (X)*x_pixel_size 
            y0_pos =  realDistY - beam_center_y + (Y)*y_pixel_size
            InPlane0_pos = np.sqrt(x0_pos**2 + y0_pos**2)
            BSS[InPlane0_pos < beamstop_diameter/2.0] = 0.0
            BeamStopShadow[dshort] = BSS
            twotheta = np.arctan2(InPlane0_pos,realDistZ)
            phi = np.arctan2(y0_pos,x0_pos)

            #Q resolution from J. of Appl. Cryst. 44, 1127-1129 (2011) and file:///C:/Users/kkrycka/Downloads/SANS_2D_Resolution.pdf where
            #there seems to be an extra factor of wavelength listed that shouldn't be there in (delta_wavelength/wavelength):
            carriage_key = dshort[0]
            if carriage_key == 'F':
                L2 = FrontDetToSample
            elif carriage_key == 'M':
                L2 = MiddleDetToSample
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
            #If no gravity correction:
            #SigmaQParlSqr = SigmaQParlSqr + np.power(Q0,2)*np.power(Wavelength_spread/np.sqrt(6.0),2)
            #Else, if adding gravity correction:
            g = 981 #in cm/s^2
            m_div_h = 252.77 #in s cm^-2
            A = -0.5*981*L2*(L1+L2)*np.power(m_div_h , 2)
            WL = Wavelength*1E-8
            SigmaQParlSqr = SigmaQParlSqr + np.power(Wavelength_spread*k/(L2),2)*(R*R -4*A*np.sin(phi)*WL*WL + 4*A*A*np.power(WL,4))/6.0 #gravity correction makes vary little difference for wavelength spread < 20%
            #VSANS IGOR 2D ASCII delta_Q seems to be way off the mark, but this 2D calculaation matches the VSANS circular average closely when pixels are converted to circular average...
            
            #This is what Greta had in comperaison, with Pixel size set to 0.82 cm:
            #deltaQ_geometry = (2.0*np.pi/(Wavelength*L2))*np.sqrt( np.power((L2*R1)/(4*L1),2) + np.power((L1+L2)/(4*L1*R1),2)+ np.power( (Pix/2.0),(2.0/3.0)) )
            #deltaQ_wavelength = Wavelength_spread/np.sqrt(6.0)
            
            Q_total[dshort] = (4.0*np.pi/Wavelength)*np.sin(twotheta/2.0)
            QQ_total = (4.0*np.pi/Wavelength)*np.sin(twotheta/2.0)
            Qx[dshort] = QQ_total*np.cos(twotheta/2.0)*np.cos(phi)
            Qy[dshort] = QQ_total*np.cos(twotheta/2.0)*np.sin(phi)
            Qz[dshort] = QQ_total*np.sin(twotheta/2.0)     
            Q_perp_unc[dshort] = np.ones_like(Q_total[dshort])*np.sqrt(SigmaQPerpSqr)
            Q_parl_unc[dshort] = np.sqrt(SigmaQParlSqr)
            #Theta_deg = 180.0*np.arctan2(Qy[dshort], Qx[dshort])/np.pi #returns values between -180.0 degrees and +180.0 degrees
            Theta_deg = phi*180.0/np.pi
        
            NM = np.ones_like(data)
            TM = np.zeros_like(data)
            BM = np.zeros_like(data)
            LUM = np.zeros_like(data)
            LLM = np.zeros_like(data)
            RM = np.zeros_like(data)
            DM1 = np.zeros_like(data)
            DM2 = np.zeros_like(data)
            DM3 = np.zeros_like(data)
            DM4 = np.zeros_like(data)
            TM[np.absolute(Theta_deg - 90.0) <= AngleWidth] = 1.0
            BM[np.absolute(Theta_deg + 90.0) <= AngleWidth] = 1.0
            
            RM[np.absolute(Theta_deg - 0.0) <= AngleWidth] = 1.0
            RM[np.absolute(Theta_deg - 360.0) <= AngleWidth] = 1.0
            LUM[np.absolute(Theta_deg - 180.0) <= AngleWidth] = 1.0
            LLM[np.absolute(Theta_deg + 180.0) <= AngleWidth] = 1.0
            LM = (LUM + LLM)
            
            DM1[np.absolute(Theta_deg - 45.0) <= AngleWidth] = 1.0
            DM2[np.absolute(Theta_deg + 135.0) <= AngleWidth] = 1.0
            DM3[np.absolute(Theta_deg - 135.0) <= AngleWidth] = 1.0
            DM4[np.absolute(Theta_deg + 45.0) <= AngleWidth] = 1.0
            QyShift = Qy[dshort] - 0.04
            SiliconWindow = np.zeros_like(data)
            SiliconWindow[np.sqrt(Qx[dshort]*Qx[dshort] + QyShift*QyShift) <= 0.123] = 1.0
            Shadow = np.zeros_like(data)
            if dshort == "MT" or dshort == "MB":
                Shadow[np.absolute(X - 64) <= 2] = 1.0
            if dshort == "ML":
                Shadow[np.absolute(Y - 68) <= 50] = 1.0
            if dshort == "ML":
                Shadow[np.absolute(X - 26) <= 1] = 0.0
            if dshort == "MR":
                Shadow[np.absolute(Y - 68) <= 50] = 1.0
            if dshort == "FT" or dshort == "FB":
                Shadow[np.absolute(X - 64) <= 40] = 1.0

            Mask_None[dshort] = NM
            Mask_Right[dshort] = RM
            Mask_Left[dshort] = LM
            Mask_Top[dshort] = TM
            Mask_Bottom[dshort] = BM
            Mask_DiagonalCW[dshort] = DM1 + DM2
            Mask_DiagonalCCW[dshort] = DM3 + DM4
            if dshort == "MT" or dshort == "MB" or dshort == "ML" or dshort == "MR":
                Mask_User_Defined[dshort] = Shadow
            else:
                Mask_User_Defined[dshort] = Shadow

            #Kludge
            if dshort == "MR":
                Mask_Right[dshort] = np.ones_like(data)
            elif dshort == "ML":
                Mask_Left[dshort] = np.ones_like(data)
            else:
                Mask_Right[dshort] = np.zeros_like(data)
                Mask_Left[dshort] = np.zeros_like(data)
            '''    
            if dshort == "MR" or dshort == "FR":
                Mask_Right[dshort] = np.ones_like(data)
                print('Right mask assigned')
            if dshort == "ML" or dshort == "FL":
                Mask_Left[dshort] = np.ones_like(data)
                print('Left mask assigned')
            '''

    return Qx, Qy, Qz, Q_total, Q_perp_unc, Q_parl_unc, dimXX, dimYY, Mask_Right, Mask_Top, Mask_Left, Mask_Bottom, Mask_DiagonalCW, Mask_DiagonalCCW, Mask_None, Mask_User_Defined, BeamStopShadow

def He3Decay_func(t, p, gamma):
    return p * np.exp(-t / gamma)

def HE3_Pol_AtGivenTime(entry_time, HE3_Cell_Summary):
    #Predefine HE3_Cell_Summary[HE3_Trans[entry]['Insert_time']] = {'Atomic_P0' : P0, 'Gamma(hours)' : gamma, 'Mu' : Mu, 'Te' : Te}
    #He3Decay_func must be predefined

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
    #Uses predefined He3Decay_func
    #Creates and returns HE3_Cell_Summary

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
            gamma = 1000.0 #assumes no appreciable time decay until more data obtained
            PCell0 = np.tanh(Mu * P0)
        else:
            popt, pcov = curve_fit(He3Decay_func, xdata, ydata)
            P0, gamma = popt
            #fit = He3Decay_func(xdata, popt[0], popt[1])
            PCell0 = np.tanh(Mu * P0)

        HE3_Cell_Summary[HE3_Trans[entry]['Insert_time']] = {'Atomic_P0' : P0, 'Gamma(hours)' : gamma, 'Mu' : Mu, 'Te' : Te}
        print('He3Cell Summary for Cell Identity', entry, ':')
        print('PolCell0', PCell0, 'AtomicPol0: ', P0, ' Gamma: ', gamma)
        print('     ')

        if xdata.size >= 2:
            print('Graphing He3 decay curve....(close generated plot to continue)')
            fit = He3Decay_func(xdata, popt[0], popt[1])
            plt.plot(xdata, ydata, 'b*', label='data')
            plt.plot(xdata, fit, 'r-', label='fit of data')
            plt.xlabel('time (hours)')
            plt.ylabel('3He atomic polarization')
            plt.title('He3 Cell Decay')
            plt.legend()
            plt.show()

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
            
            plt.plot(xdata, TMAJ_data, 'b*', label='T_MAJ data')
            plt.plot(xdataextended, TMAJ_fit, 'c-', label='T_MAJ predicted')

            plt.plot(xdata, TMIN_data, 'r*', label='T_MIN data')
            plt.plot(xdataextended, TMIN_fit, 'm-', label='T_MIN predicted')
            
            plt.xlabel('time (hours)')
            plt.ylabel('Spin Transmission')
            plt.title('Predicted He3 Cell Transmission')
            plt.legend()
            plt.show()
            
        #NeutronPol = np.tanh(Mu * AtomicPol)
        #UnpolHE3Trans = Te * np.exp(-Mu)*np.cosh(Mu * AtomicPol)
        #T_MAJ = Te * np.exp(-Mu*(1.0 - AtomicPol))
        #T_MIN = Te * np.exp(-Mu*(1.0 + AtomicPol))

    return HE3_Cell_Summary

def Pol_SuppermirrorAndFlipper(Pol_Trans, HE3_Cell_Summary):
    #Uses time of measurement from Pol_Trans,
    #saves PSM and PF values into Pol_Trans.
    #Uses prefefined HE3_Pol_AtGivenTime function.
    
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
            print('UU_Cell', UU_NeutronPol, UU_UnpolHe3Trans)
            print('DU_Cell', DU_NeutronPol, DU_UnpolHe3Trans)
            print('DD_Cell', DD_NeutronPol, DD_UnpolHe3Trans)
            print('UD_Cell', UD_NeutronPol, UD_UnpolHe3Trans)

            '''
            #Division method:
            print('  ')
            PF = 1.00
            Pol_Trans[ID]['P_F'] = np.average(PF)
            PSM1 = (DD/DD_UnpolHe3Trans - DU/DU_UnpolHe3Trans)/(DU_NeutronPol*DD/DD_UnpolHe3Trans+DD_NeutronPol*DU/DU_UnpolHe3Trans)
            PSM2 = (UU/UU_UnpolHe3Trans - UD/UD_UnpolHe3Trans)/(UD_NeutronPol*UU/UU_UnpolHe3Trans+UU_NeutronPol*UD/UD_UnpolHe3Trans)
            PSM = (PSM1 + PSM2)/ 2.0
            Pol_Trans[ID]['P_SM'] = np.average(PSM)
            print('Ave P_SM is', Pol_Trans[ID]['P_SM'])
            '''
            #Direct transmission method:
            PF = 1.00
            Pol_Trans[ID]['P_F'] = np.average(PF)
            PSMUU = (UU/UU_UnpolHe3Trans - 1.0)/(UU_NeutronPol)
            PSMDD = (DD/DD_UnpolHe3Trans - 1.0)/(DD_NeutronPol)
            PSMUD = (1.0 - UD/UD_UnpolHe3Trans)/(UD_NeutronPol)
            PSMDU = (1.0 - DU/DU_UnpolHe3Trans)/(DU_NeutronPol)
            PSM_Ave = 0.25*(np.average(PSMUU) + np.average(PSMDD) + np.average(PSMUD) + np.average(PSMDU))
            Pol_Trans[ID]['P_SM'] = np.average(PSM_Ave)
            print('PSM', Pol_Trans[ID]['P_SM'])
            

            if UsePolCorr == 0:#0 Means no, turn it off
                Pol_Trans[ID]['P_SM'] = 1.0
                Pol_Trans[ID]['P_F'] = 1.0
                print('Manually reset P_SM and P_F to unity')

    return

def GlobalAbsScaleAndPolCorr(Sample, Config, BlockBeam_per_second, Solid_Angle, YesNoSubtraction, SubtractionArray):

    #Full-Pol Reduction
    Scaled_Data = np.zeros((8,4,6144))
    UncScaled_Data = np.zeros((8,4,6144))
    masks = {}
    BB = {}
    Pol_Efficiency = np.zeros((4,4))
    HE3_Efficiency = np.zeros((4,4))
    PolCorr_AllDetectors = {}
    HE3Corr_AllDetectors = {}
    Uncertainty_PolCorr_AllDetectors = {}
    Have_FullPol = 0
    if Sample in Trans and str(Scatt[Sample]['Config(s)'][Config]['UU']).find('NA') == -1 and str(Scatt[Sample]['Config(s)'][Config]['DU']).find('NA') == -1 and str(Scatt[Sample]['Config(s)'][Config]['DD']).find('NA') == -1 and str(Scatt[Sample]['Config(s)'][Config]['UD']).find('NA') == -1:
        Have_FullPol = 1
        if 'U_Trans_Cts' in Trans[Sample]['Config(s)'][Config]:
            ABS_Scale = np.average(np.array(Trans[Sample]['Config(s)'][Config]['U_Trans_Cts']))
        else:
            ABS_Scale = 1.0
        if Sample in Pol_Trans:
            PSM = Pol_Trans[Sample]['P_SM']
            PF = Pol_Trans[Sample]['P_F']
            print(Sample, Config, 'PSM is', PSM, 'PF is', PF)
        else:
            print(Sample, Config, 'missing P_F and P_SM; will proceed without pol-correction!')
            PF = 1.0
            PSM = 1.0
        #Calculating an average block beam counts per pixel and time (seems to work better than a pixel-by-pixel subtraction, at least for shorter count times)
        for dshort in short_detectors:
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

        Number_UU = 1.0*len(Scatt[Sample]['Config(s)'][Config]["UU"])
        Number_DU = 1.0*len(Scatt[Sample]['Config(s)'][Config]["DU"])
        Number_DD = 1.0*len(Scatt[Sample]['Config(s)'][Config]["DD"])
        Number_UD = 1.0*len(Scatt[Sample]['Config(s)'][Config]["UD"])
            
        Scatt_Type = ["UU", "DU", "DD", "UD"]
        for type in Scatt_Type:
            type_time = type + "_Time"
            filenumber_counter = 0
            for filenumber in Scatt[Sample]['Config(s)'][Config][type]:
                filename = path + "sans" + str(filenumber) + ".nxs.ngv"
                config = Path(filename)
                if config.is_file():
                    f = h5py.File(filename)
                    MonCounts = f['entry/control/monitor_counts'][0]
                    Count_time = f['entry/collection_time'][0]
                    entry = Scatt[Sample]['Config(s)'][Config][type_time][filenumber_counter]
                    NP, UT, T_MAJ, T_MIN = HE3_Pol_AtGivenTime(entry, HE3_Cell_Summary)
                    C = NP
                    S = 0.998 #0.9985 is the highest I've recently gotten at 5.5 Ang and it could even be 1.0 with tight slits..., from EuSe 60 nm 0.95 V and 2.0 K
                    X = np.sqrt(PSM/S) #also try np.sqrt(PSM*1.005/S with S = 1.0
                    if type == "UU":
                        CrossSection_Index = 0
                        UT = UT / Number_UU
                        Pol_Efficiency[CrossSection_Index][:] += [(C*(S*X*X + X) + S*X + 1)*UT, (C*(-S*X*X + X) - S*X + 1)*UT, (C*(S*X*X - X) - S*X + 1)*UT, (C*(-S*X*X - X) + S*X + 1)*UT]
                        HE3_Efficiency[CrossSection_Index][:] += [ UT, 0.0, 0.0, 0.0]
                        Det_Index = 0
                        for dshort in short_detectors:
                            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            unc = np.sqrt(data)
                            data = (data - Count_time*BB[dshort])/Number_UU
                            #Hold = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            #data = np.ones_like(Hold)*1000/Number_UU
                            Scaled_Data[Det_Index][CrossSection_Index][:] += ((1E8/MonCounts)/ABS_Scale)*data.flatten()
                            UncScaled_Data[Det_Index][CrossSection_Index][:] += ((1E8/MonCounts)/ABS_Scale)*unc.flatten()
                            Det_Index += 1
                    elif type == "DU":
                        CrossSection_Index = 1
                        UT = UT / Number_DU
                        Pol_Efficiency[CrossSection_Index][:] += [(C*(-S*X*X + X) - S*X + 1)*UT, (C*(S*X*X + X) + S*X + 1)*UT, (C*(-S*X*X - X) + S*X + 1)*UT, (C*(S*X*X - X) - S*X + 1)*UT]
                        HE3_Efficiency[CrossSection_Index][:] += [ 0.0, UT, 0.0, 0.0]
                        Det_Index = 0
                        for dshort in short_detectors:
                            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            unc = np.sqrt(data)
                            data = (data - Count_time*BB[dshort])/Number_DU
                            #Hold = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            #data = np.ones_like(Hold)*1000/Number_DU
                            unc = unc/Number_DU
                            Scaled_Data[Det_Index][CrossSection_Index][:] += ((1E8/MonCounts)/ABS_Scale)*data.flatten()
                            UncScaled_Data[Det_Index][CrossSection_Index][:] += ((1E8/MonCounts)/ABS_Scale)*unc.flatten()
                            Det_Index += 1
                    elif type == "DD":
                        CrossSection_Index = 2
                        UT = UT / Number_DD
                        Pol_Efficiency[CrossSection_Index][:] += [(C*(S*X*X - X) - S*X + 1)*UT, (C*(-S*X*X - X) + S*X + 1)*UT, (C*(S*X*X + X) + S*X + 1)*UT, (C*(-S*X*X + X) - S*X + 1)*UT]
                        HE3_Efficiency[CrossSection_Index][:] += [ 0.0, 0.0, UT, 0.0]
                        Det_Index = 0
                        for dshort in short_detectors:
                            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            unc = np.sqrt(data)
                            data = (data - Count_time*BB[dshort])/Number_DD
                            #Hold = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            #data = np.ones_like(Hold)*1000/Number_DD
                            Scaled_Data[Det_Index][CrossSection_Index][:] += ((1E8/MonCounts)/ABS_Scale)*data.flatten()
                            UncScaled_Data[Det_Index][CrossSection_Index][:] += ((1E8/MonCounts)/ABS_Scale)*unc.flatten()
                            Det_Index += 1
                    elif type == "UD":
                        CrossSection_Index = 3
                        UT = UT / Number_UD
                        Pol_Efficiency[CrossSection_Index][:] += [(C*(-S*X*X - X) + S*X + 1)*UT, (C*(S*X*X - X) - S*X + 1)*UT, (C*(-S*X*X + X) - S*X + 1)*UT, (C*(S*X*X + X) + S*X + 1)*UT]
                        HE3_Efficiency[CrossSection_Index][:] += [ 0.0, 0.0, 0.0, UT]
                        Det_Index = 0
                        for dshort in short_detectors:
                            data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            unc = np.sqrt(data)
                            data = (data - Count_time*BB[dshort])/Number_UD
                            #Hold = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=dshort)])
                            #data = np.ones_like(Hold)*1000/Number_UD
                            unc = unc/Number_UD
                            Scaled_Data[Det_Index][CrossSection_Index][:] += ((1E8/MonCounts)/ABS_Scale)*data.flatten()
                            UncScaled_Data[Det_Index][CrossSection_Index][:] += ((1E8/MonCounts)/ABS_Scale)*unc.flatten()
                            Det_Index += 1
                            
                filenumber_counter += 1

        
        Prefactor = inv(Pol_Efficiency)
        PrefactorII = inv(HE3_Efficiency)
        Det_Index = 0
        for dshort in short_detectors:
            UncData_Per_Detector = UncScaled_Data[Det_Index][:][:]
            Data_Per_Detector = Scaled_Data[Det_Index][:][:]
            HE3Corr_Data = np.dot(PrefactorII, Data_Per_Detector)
            if YesNoSubtraction > 0:
                if dshort in middle_detectors:
                    Data_Per_Detector = Data_Per_Detector - (SubtractionArray[dshort]*Plex[dshort]*Solid_Angle[dshort])
                    print('Subtracting background')
            PolCorr_Data = np.dot(Prefactor, Data_Per_Detector)
            '''
            #Below is the code that allows true matrix error propagation, but it takes a while...so may want to optimize more before impleneting.
            #Also will need to uncomment from uncertainties import unumpy (top).
            Data_Per_Detector2 = unumpy.umatrix(Scaled_Data[Det_Index][:][:], UncScaled_Data[Det_Index][:][:])
            PolCorr_Data2 = np.dot(Prefactor, Data_Per_Detector2)
            PolCorr_Data = unumpy.nominal_values(PolCorr_Data2)
            PolCorr_Unc = unumpy.std_devs(PolCorr_Data2)
            '''
            PolCorr_AllDetectors[dshort] = PolCorr_Data / (Plex[dshort]*Solid_Angle[dshort])
            Uncertainty_PolCorr_AllDetectors[dshort] = UncData_Per_Detector / (Plex[dshort]*Solid_Angle[dshort])
            HE3Corr_AllDetectors[dshort] = HE3Corr_Data / (Plex[dshort]*Solid_Angle[dshort])
            Det_Index += 1

    return PolCorr_AllDetectors, Uncertainty_PolCorr_AllDetectors, HE3Corr_AllDetectors, Have_FullPol

def MinMaxQ(Q_total):

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
    Q_min = MinQ_Middle 
    Q_max = MaxQ_Front

    return Q_min, Q_max

def SliceData(Slice_Type, Q_min, Q_max, Q_bins, QGridPerDetector, masks, PolCorr_AllDetectors, Unc_PolCorr_AllDetectors, dimXX, dimYY, ID, Config, PlotYesNo):
    
    Key = Slice_Type
    print('Plotting and saving {type} cuts for GroupID {idnum} at Configuration {cf}'.format(type=Key, idnum=ID, cf = Config))
    Q_Values = np.linspace(Q_min, Q_max, Q_bins, endpoint=True)
    Q_step = (Q_max - Q_min) / Q_bins
    
    FrontUU = np.zeros_like(Q_Values)
    FrontDU = np.zeros_like(Q_Values)
    FrontDD = np.zeros_like(Q_Values)
    FrontUD = np.zeros_like(Q_Values)
    FrontUU_Unc = np.zeros_like(Q_Values)
    FrontDU_Unc = np.zeros_like(Q_Values)
    FrontDD_Unc = np.zeros_like(Q_Values)
    FrontUD_Unc = np.zeros_like(Q_Values) 
    FrontMeanQ = np.zeros_like(Q_Values)
    FrontMeanQUnc = np.zeros_like(Q_Values)
    FrontPixels = np.zeros_like(Q_Values)
    
    MiddleUU = np.zeros_like(Q_Values)
    MiddleDU = np.zeros_like(Q_Values)
    MiddleDD = np.zeros_like(Q_Values)
    MiddleUD = np.zeros_like(Q_Values)
    MiddleUU_Unc = np.zeros_like(Q_Values)
    MiddleDU_Unc = np.zeros_like(Q_Values)
    MiddleDD_Unc = np.zeros_like(Q_Values)
    MiddleUD_Unc = np.zeros_like(Q_Values)
    MiddleMeanQ = np.zeros_like(Q_Values)
    MiddleMeanQUnc = np.zeros_like(Q_Values)
    MiddlePixels = np.zeros_like(Q_Values)
    
    for dshort in short_detectors:
        dimX = dimXX[dshort]
        dimY = dimYY[dshort]
        Q_tot = QGridPerDetector['Q_total'][dshort][:][:]
        Q_unc = np.sqrt(np.power(QGridPerDetector['Q_perp_unc'][dshort][:][:],2) + np.power(QGridPerDetector['Q_parl_unc'][dshort][:][:],2))
        UU = PolCorr_AllDetectors[dshort][0][:][:]
        UU = UU.reshape((dimX, dimY))
        DU = PolCorr_AllDetectors[dshort][1][:][:]
        DU = DU.reshape((dimX, dimY))
        DD = PolCorr_AllDetectors[dshort][2][:][:]
        DD = DD.reshape((dimX, dimY))
        UD = PolCorr_AllDetectors[dshort][3][:][:]
        UD = UD.reshape((dimX, dimY))
        UU_Unc = Unc_PolCorr_AllDetectors[dshort][0][:][:]
        UU_Unc = UU_Unc.reshape((dimX, dimY))
        DU_Unc = Unc_PolCorr_AllDetectors[dshort][1][:][:]
        DU_Unc = DU_Unc.reshape((dimX, dimY))
        DD_Unc = Unc_PolCorr_AllDetectors[dshort][2][:][:]
        DD_Unc = DD_Unc.reshape((dimX, dimY))
        UD_Unc = Unc_PolCorr_AllDetectors[dshort][3][:][:]
        UD_Unc = UD_Unc.reshape((dimX, dimY))

        Exp_bins = np.linspace(Q_min, Q_max + Q_step, Q_bins + 1, endpoint=True)
        countsUU, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=UU[masks[dshort] > 0])
        countsDU, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=DU[masks[dshort] > 0])
        countsDD, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=DD[masks[dshort] > 0])
        countsUD, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=UD[masks[dshort] > 0])
        
        UncUU, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=np.power(UU_Unc[masks[dshort] > 0],2))
        UncDU, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=np.power(DU_Unc[masks[dshort] > 0],2))
        UncDD, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=np.power(DD_Unc[masks[dshort] > 0],2))
        UncUD, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=np.power(UD_Unc[masks[dshort] > 0],2))
        
        MeanQSum, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=Q_tot[masks[dshort] > 0])
        MeanQUnc, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=np.power(Q_unc[masks[dshort] > 0],2)) 
        pixels, _ = np.histogram(Q_tot[masks[dshort] > 0], bins=Exp_bins, weights=np.ones_like(UU)[masks[dshort] > 0])  
        carriage_key = dshort[0]
        if carriage_key == 'F':
            FrontUU += countsUU
            FrontDU += countsDU
            FrontDD += countsDD
            FrontUD += countsUD
            FrontUU_Unc += UncUU
            FrontDU_Unc += UncDU
            FrontDD_Unc += UncDD
            FrontUD_Unc += UncUD
            FrontMeanQ += MeanQSum
            FrontMeanQUnc += MeanQUnc
            FrontPixels += pixels
        elif carriage_key == 'M':
            MiddleUU += countsUU
            MiddleDU += countsDU
            MiddleDD += countsDD
            MiddleUD += countsUD
            MiddleUU_Unc += UncUU
            MiddleDU_Unc += UncDU
            MiddleDD_Unc += UncDD
            MiddleUD_Unc += UncUD
            MiddleMeanQ += MeanQSum
            MiddleMeanQUnc += MeanQUnc
            MiddlePixels += pixels

    nonzero_front_mask = (FrontPixels > 0) #True False map
    nonzero_middle_mask = (MiddlePixels > 0) #True False map
    Q_Front = Q_Values[nonzero_front_mask]
    MeanQ_Front = FrontMeanQ[nonzero_front_mask] / FrontPixels[nonzero_front_mask]
    MeanQUnc_Front = np.sqrt(FrontMeanQUnc[nonzero_front_mask]) / FrontPixels[nonzero_front_mask]
    UUF = FrontUU[nonzero_front_mask] / FrontPixels[nonzero_front_mask]
    DUF = FrontDU[nonzero_front_mask] / FrontPixels[nonzero_front_mask]
    DDF = FrontDD[nonzero_front_mask] / FrontPixels[nonzero_front_mask]
    UDF = FrontUD[nonzero_front_mask] / FrontPixels[nonzero_front_mask]
    Q_Middle = Q_Values[nonzero_middle_mask]
    MeanQ_Middle = MiddleMeanQ[nonzero_middle_mask] / MiddlePixels[nonzero_middle_mask]
    MeanQUnc_Middle = np.sqrt(MiddleMeanQUnc[nonzero_middle_mask]) / MiddlePixels[nonzero_middle_mask]
    UUM = MiddleUU[nonzero_middle_mask] / MiddlePixels[nonzero_middle_mask]
    DUM = MiddleDU[nonzero_middle_mask] / MiddlePixels[nonzero_middle_mask]
    DDM = MiddleDD[nonzero_middle_mask] / MiddlePixels[nonzero_middle_mask]
    UDM = MiddleUD[nonzero_middle_mask] / MiddlePixels[nonzero_middle_mask]

    Sigma_UUF = np.sqrt(FrontUU_Unc[nonzero_front_mask]) / FrontPixels[nonzero_front_mask]
    Sigma_DUF = np.sqrt(FrontDU_Unc[nonzero_front_mask]) / FrontPixels[nonzero_front_mask]
    Sigma_DDF = np.sqrt(FrontDD_Unc[nonzero_front_mask]) / FrontPixels[nonzero_front_mask]
    Sigma_UDF = np.sqrt(FrontUD_Unc[nonzero_front_mask]) / FrontPixels[nonzero_front_mask]
    Sigma_UUM = np.sqrt(MiddleUU_Unc[nonzero_middle_mask]) / MiddlePixels[nonzero_middle_mask]
    Sigma_DUM = np.sqrt(MiddleDU_Unc[nonzero_middle_mask]) / MiddlePixels[nonzero_middle_mask]
    Sigma_DDM = np.sqrt(MiddleDD_Unc[nonzero_middle_mask]) / MiddlePixels[nonzero_middle_mask]
    Sigma_UDM = np.sqrt(MiddleUD_Unc[nonzero_middle_mask]) / MiddlePixels[nonzero_middle_mask]
    
    Q_Common = np.concatenate((Q_Middle, Q_Front), axis=0)
    Q_Mean = np.concatenate((MeanQ_Middle, MeanQ_Front), axis=0)
    Q_Uncertainty = np.concatenate((MeanQUnc_Middle, MeanQUnc_Front), axis=0)
    UU = np.concatenate((UUM, UUF), axis=0)
    DU = np.concatenate((DUM, DUF), axis=0)
    DD = np.concatenate((DDM, DDF), axis=0)
    UD = np.concatenate((UDM, UDF), axis=0)
    SigmaUU = np.concatenate((Sigma_UUM, Sigma_UUF), axis=0)
    SigmaDU = np.concatenate((Sigma_DUM, Sigma_DUF), axis=0)
    SigmaDD = np.concatenate((Sigma_DDM, Sigma_DDF), axis=0)
    SigmaUD = np.concatenate((Sigma_UDM, Sigma_UDF), axis=0)
    Shadow = np.ones_like(Q_Common)

    if PlotYesNo == 1:
        fig = plt.figure()
        '''
        ax = plt.axes()
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.errorbar(Q_Front, UUF, yerr=Sigma_UUF, fmt = 'b*', label='Front, UU')
        ax.errorbar(Q_Middle, UUM, yerr=Sigma_UUM, fmt = 'g*', label='Middle, UU')
        ax.errorbar(Q_Front, DDF, yerr=Sigma_DDF, fmt = 'm*', label='Front, DD')
        ax.errorbar(Q_Middle, DDM, yerr=Sigma_DDM, fmt = 'r*', label='Middle, DD')
        ax.errorbar(Q_Front, DUF, yerr=Sigma_DUF, fmt = 'c.', label='Front, DU')
        ax.errorbar(Q_Middle, DUM, yerr=Sigma_DUM, fmt = 'm.', label='Middle, DU')
        ax.errorbar(Q_Front, UDF, yerr=Sigma_UDF, fmt = 'y.', label='Front, UD')
        ax.errorbar(Q_Middle, UDM, yerr=Sigma_UDM, fmt = 'b.', label='Middle, UD')
        '''
        #If don't want to plot error bars, use something like plt.loglog(Q_Front, UUF, 'b*', label='Front, UU')
        plt.loglog(Q_Front, UUF, 'b*', label='Front, UU')
        plt.loglog(Q_Middle, UUM, 'g*', label='Middle, UU')
        plt.loglog(Q_Front, DDF, 'm*', label='Front, DD')
        plt.loglog(Q_Middle, DDM, 'r*', label='Middle, DD')
        plt.loglog(Q_Front, DUF, 'c.', label='Front, DU')
        plt.loglog(Q_Middle, DUM, 'm.', label='Middle, DU')
        plt.loglog(Q_Front, UDF, 'y.', label='Front, UD')
        plt.loglog(Q_Middle, UDM, 'b.', label='Middle, UD')

        plt.xlabel('Q')
        plt.ylabel('Intensity')
        plt.title('FullPol_{keyword}Cuts for ID = {idnum} and Config = {cf}'.format(keyword=Key, idnum=ID, cf = Config))
        plt.legend()
        fig.savefig('{keyword}FullPol_Cuts_ID{idnum}_CF{cf}.png'.format(keyword=Key, idnum=ID, cf = Config))
        plt.show()

        '''

        SFF = DUF + DUF
        Sigma_SFF = np.sqrt(np.power(Sigma_DUF,2) + np.power(Sigma_UDF,2))
        SFM = DUM + DUM
        Sigma_SFM = np.sqrt(np.power(Sigma_DUM,2) + np.power(Sigma_UDM,2))

        NSFF = UUF + DDF
        Sigma_NSFF = np.sqrt(np.power(Sigma_UUF,2) + np.power(Sigma_DDF,2))
        NSFM = UUM + DDM
        Sigma_NSFM = np.sqrt(np.power(Sigma_UUM,2) + np.power(Sigma_DDM,2))
 
        fig = plt.figure()
        #If don't want to plot error bars, use something like plt.loglog(Q_Front, UUF, 'b*', label='Front, UU')
        plt.loglog(Q_Middle, NSFM, 'm*', label='Middle, UU + DD')
        plt.loglog(Q_Front, NSFF, 'r*', label='Front, UU + DD')
        plt.loglog(Q_Middle, SFM, 'b*', label='Middle, UD + DU')
        plt.loglog(Q_Front, SFF, 'g*', label='Front, UD + DU')
        plt.xlabel('Q')
        plt.ylabel('Intensity')
        plt.title('FullPol_{keyword}Cuts for ID = {idnum} and Config = {cf}'.format(keyword=Key, idnum=ID, cf = Config))
        plt.legend()
        fig.savefig('{keyword}FullPol_Combined_ID{idnum}_CF{cf}.png'.format(keyword=Key, idnum=ID, cf = Config))
        plt.show()
        

        SF = UD + DU
        SF_Unc = np.sqrt(np.power(SigmaDU,2) + np.power(SigmaUD,2))
        NSF = UU + DD
        NSF_Unc = np.sqrt(np.power(SigmaUU,2) + np.power(SigmaDD,2))
        NSFDiff = DD - UU

        text_output = np.array([Q_Common, UU, SigmaUU, DU, SigmaDU, DD, SigmaDD, UD, SigmaUD, Q_Uncertainty, Q_Mean, Shadow])
        text_output = text_output.T
        np.savetxt('{key}FullPol_ID={idnum}Config={cf}.txt'.format(key=Key, idnum=ID, cf = Config), text_output, header='Q, UU, DelUU, DU, DelUD, DD, DelDD, UD, DelUD, DQ, MeanQ, Shadow', fmt='%1.4e')

        text_output2 = np.array([Q_Common, SF, SF_Unc, NSF, NSF_Unc, NSFDiff, Q_Uncertainty, Q_Mean, Shadow])
        text_output2 = text_output2.T
        np.savetxt('{key}FullPol_ID={idnum}Config={cf}.txt'.format(key=Key, idnum=ID, cf = Config), text_output2, header='Q, SF, DelSF, NSF, DelNSF, NSFDiff, DelQ, MeanQ, Shadow', fmt='%1.4e')
        '''
        
    Output = {}
    Output['Q_Common'] = Q_Common
    Output['Q_Mean'] = Q_Mean
    Output['UU'] = UU
    Output['UU_Unc'] = SigmaUU
    Output['DU'] = DU
    Output['DU_Unc'] = SigmaDU
    Output['DD'] = DD
    Output['DD_Unc'] = SigmaDU
    Output['UD'] = UD
    Output['UD_Unc'] = SigmaUD
    Output['Q_Uncertainty'] = Q_Uncertainty
    Output['Q_Mean'] = Q_Mean
    Output['Shadow'] = Shadow
     
    return Output


def ASCIIlike_Output(Type, ID, Config, Data_AllDetectors, Unc_Data_AllDetectors, QGridPerDetector):

    for dshort in short_detectors:

        Q_tot = QGridPerDetector['Q_total'][dshort][:][:]
        Q_unc = np.sqrt(np.power(QGridPerDetector['Q_perp_unc'][dshort][:][:],2) + np.power(QGridPerDetector['Q_parl_unc'][dshort][:][:],2))
        QQX = QGridPerDetector['QX'][dshort][:][:]
        QQX = QQX.T
        QXData = QQX.flatten()
        QQY = QGridPerDetector['QY'][dshort][:][:]
        QQY = QQY.T
        QYData = QQY.flatten()
        QQZ = QGridPerDetector['QZ'][dshort][:][:]
        QQZ = QQZ.T
        QZData = QQZ.flatten()
        QPP = QGridPerDetector['Q_perp_unc'][dshort][:][:]
        QPP = QPP.T
        QPerpUnc = QPP.flatten()
        QPR = QGridPerDetector['Q_parl_unc'][dshort][:][:]
        QPR = QPR.T
        QParlUnc = QPR.flatten()
        Shadow = np.ones_like(Q_tot)

        if Type == 'Unpol':
            print('Outputting Unpol data into ASCII-like format for {det}, GroupID = {idnum} '.format(det=dshort, idnum=ID))
            Intensity = Data_AllDetectors[dshort]
            Intensity = Intensity.T
            Int = Intensity.flatten()
            IntensityUnc = Unc_Data_AllDetectors[dshort]
            IntensityUnc = IntensityUnc.T
            DeltaInt = IntensityUnc.flatten()
            ASCII_like = np.array([QXData, QYData, Int, DeltaInt, QZData, QParlUnc, QPerpUnc])
            ASCII_like = ASCII_like.T
            np.savetxt('UnpolScatt_{det}.DAT'.format(det=dshort), ASCII_like, header='Qx, Qy, I, DI, Qz, UncQParl, UncQPerp', fmt='%1.4e')
            #np.savetxt('UnpolScatt_ID={idnum}_{CF}_{det}.DAT'.format(idnum=ID, CF=Config, det=dshort), ASCII_like, header='Qx, Qy, I, DI, Qz, UncQParl, UncQPerp, Shadow', fmt='%1.4e')
            #np.savetxt('Unpol_ID={idnum}_(CF}_{det}.DAT'.format(idnum=ID, CF=Config, det=dshort), ASCII_like, header='Qx, Qy, I, DI, QZ, UncQParl, UncQPerp, Shadow', fmt='%1.4e')
        if Type == 'Fullpol':
            print('Outputting Fullpol data into ASCII-like format for {det}, GroupID = {idnum} '.format(det=dshort, idnum=ID))
            Intensity_FourCrossSections = Data_AllDetectors[dshort]
            Uncertainty_FourCrossSections = Unc_Data_AllDetectors[dshort]
            Cross_Section = 0
            List = ['UU', 'DU', 'DD', 'UD']
            while Cross_Section < 4:
                Intensity = Intensity_FourCrossSections[Cross_Section][:][:]
                Intensity = Intensity.T
                Int = Intensity.flatten()
                Uncertainty = Uncertainty_FourCrossSections[Cross_Section][:][:]
                Uncertainty = Uncertainty.T
                DeltaInt = Uncertainty.flatten()
                ASCII_like = np.array([QXData, QYData, Int, DeltaInt, QZData, QParlUnc, QPerpUnc])
                ASCII_like = ASCII_like.T
                np.savetxt('{TP}Scatt_ID={idnum}_{CF}_{det}.DAT'.format(TP = List[Cross_Section], idnum=ID, CF=Config, det=dshort), ASCII_like, header='Qx, Qy, I, DI, Qz, UncQParl, UncQPerp', fmt='%1.4e')
                Cross_Section += 1

    return

#*************************************************
#***        Start of 'The Program'             ***
#*************************************************

Sample_Names, Configs, BlockBeam, Scatt, Trans, Pol_Trans, HE3_Trans = SortDataAutomatic(YesNoManualHe3Entry, New_HE3_Files, MuValues, TeValues)

Process_ScattFiles()

Masks = ReadIn_Masks()

Process_Transmissions(BlockBeam, Masks, HE3_Trans, Pol_Trans, Trans)

HE3_Cell_Summary = HE3_DecayCurves(HE3_Trans)

Pol_SuppermirrorAndFlipper(Pol_Trans, HE3_Cell_Summary)

Plex = Plex_File()

Trunc_mask = {}
Slice_mask = {}
FullPolEmpty = {}
FullPolResults = {}
QValues_All = {}
for Config in Configs:
    representative_filenumber = Configs[Config]
    Solid_Angle = SolidAngle_AllDetectors(representative_filenumber)
    BB_per_second = BlockedBeamScattCountsPerSecond(Config, representative_filenumber)
    QX, QY, QZ, Q_total, Q_perp_unc, Q_parl_unc, dimXX, dimYY, Right_mask, Top_mask, Left_mask, Bottom_mask, DiagCW_mask, DiagCCW_mask, No_mask, Mask_User_Definedm, Shadow = QCalculationAndMasks_AllDetectors(representative_filenumber, SectorCutAngles)
    QValues_All = {'QX':QX,'QY':QY,'QZ':QZ,'Q_total':Q_total,'Q_perp_unc':Q_perp_unc,'Q_parl_unc':Q_parl_unc}
    Q_min, Q_max = MinMaxQ(Q_total)
    Q_bins = 180 #120
    for Slice in sector_slices:
        for dshort in short_detectors:
            if str(Slice).find('Circ') != -1:
                Trunc_mask[dshort] = No_mask[dshort]
            elif str(Slice).find('Vert') != -1:
                Trunc_mask[dshort] = Top_mask[dshort] + Bottom_mask[dshort]
            elif str(Slice).find('Top') != -1:
                Trunc_mask[dshort] = Top_mask[dshort]
            elif str(Slice).find('Bottom') != -1:
                Trunc_mask[dshort] = Bottom_mask[dshort]
            elif str(Slice).find('Horz') != -1:
                Trunc_mask[dshort] = Left_mask[dshort] +  Right_mask[dshort]
            elif str(Slice).find('Left') != -1:
                Trunc_mask[dshort] = Left_mask[dshort]
            elif str(Slice).find('Right') != -1:
                Trunc_mask[dshort] = Right_mask[dshort]
            elif str(Slice).find('Diag') != -1:
                Trunc_mask[dshort] = DiagCW_mask[dshort] +  DiagCCW_mask[dshort]
        '''
        if Config in Masks:
            if 'NA' not in Masks[Config]['Scatt_WithSolenoid']:
                for dshort in short_detectors:
                    Trunc_mask[dshort] = Trunc_mask[dshort]*Masks[Config]['Scatt_WithSolenoid'][dshort]
            elif 'NA' not in Masks[Config]['Scatt_Standard']:
                for dshort in short_detectors:
                    Trunc_mask[dshort] = Trunc_mask[dshort]*Masks[Config]['Scatt_Standard'][dshort]
                    '''
        HaveFullPolEmpty = 0
        Empty_HE3Corr_AllDetectors = np.array([0,0,0,0])
        for Sample in Sample_Names:
            if Sample in Scatt:
                if str(Scatt[Sample]['Intent']).find('Empty') != -1:
                    if Config in Scatt[Sample]['Config(s)']:
                        SubtractionForEmpty = 0
                        Holder = np.array([0,0,0,0])
                        PolCorr_AllDetectors, Uncertainty_PolCorr_AllDetectors, Empty_HE3Corr_AllDetectors, FullPolGo = GlobalAbsScaleAndPolCorr(Sample, Config, BB_per_second, Solid_Angle, SubtractionForEmpty, Holder)
                        if FullPolGo > 0:
                            EmptyPlotYesNo = 1
                            FullPolEmpty[Slice] = SliceData(Slice, Q_min, Q_max, Q_bins, QValues_All, Trunc_mask, PolCorr_AllDetectors, Uncertainty_PolCorr_AllDetectors, dimXX, dimYY, Sample, Config, EmptyPlotYesNo)
                            HaveFullPolEmpty = 1
        #Kludge:
        HaveFullPolEmpty = 0                        
        for Sample in Sample_Names:
            if Sample in Scatt:                
                if str(Scatt[Sample]['Intent']).find('Sample') != -1:
                    if Config in Scatt[Sample]['Config(s)']:
                        YesNoSubtraction = 0
                        PolCorr_AllDetectors, Uncertainty_PolCorr_AllDetectors, HE3Corr_AllDetectors, FullPolGo = GlobalAbsScaleAndPolCorr(Sample, Config, BB_per_second, Solid_Angle, YesNoSubtraction, Empty_HE3Corr_AllDetectors)
                        if FullPolGo > 0:
                            FullPolResults[Slice] = SliceData(Slice, Q_min, Q_max, Q_bins, QValues_All, Trunc_mask, PolCorr_AllDetectors, Uncertainty_PolCorr_AllDetectors, dimXX, dimYY, Sample, Config, PlotYesNo)
                            Q = FullPolResults[Slice]['Q_Common']

                            if HaveFullPolEmpty == 1:
                                FullPolResults[Slice]['NSFAdd'] = (FullPolResults[Slice]['UU'] - FullPolEmpty[Slice]['UU']) +  (FullPolResults[Slice]['DD'] - FullPolEmpty[Slice]['DD'])
                                FullPolResults[Slice]['NSFDiff'] = (FullPolResults[Slice]['DD'] - FullPolResults[Slice]['UU'])
                                FullPolResults[Slice]['NSFUnc'] = np.sqrt(np.power(FullPolResults[Slice]['DD_Unc'],2) + np.power(FullPolResults[Slice]['UU_Unc'],2))
                                FullPolResults[Slice]['SFAdd'] = (FullPolResults[Slice]['UD'] - FullPolEmpty[Slice]['UD']) +  (FullPolResults[Slice]['DU'] - FullPolEmpty[Slice]['DU'])
                                FullPolResults[Slice]['SFUnc'] = np.sqrt(np.power(FullPolResults[Slice]['UD_Unc'],2) + np.power(FullPolResults[Slice]['DU_Unc'],2))
                                
                            else:
                                FullPolResults[Slice]['NSFAdd'] = (FullPolResults[Slice]['UU']) +  (FullPolResults[Slice]['DD'])
                                FullPolResults[Slice]['NSFDiff'] = (FullPolResults[Slice]['DD'] - FullPolResults[Slice]['UU'])
                                FullPolResults[Slice]['SFAdd'] = (FullPolResults[Slice]['UD']) +  (FullPolResults[Slice]['DU'])
                                FullPolResults[Slice]['NSFUnc'] = np.sqrt(np.power(FullPolResults[Slice]['DD_Unc'],2) + np.power(FullPolResults[Slice]['UU_Unc'],2))
                                FullPolResults[Slice]['SFUnc'] = np.sqrt(np.power(FullPolResults[Slice]['UD_Unc'],2) + np.power(FullPolResults[Slice]['DU_Unc'],2))

                            '''
                            YesNoErrorBars = 1
                            fig = plt.figure()
                            if YesNoErrorBars == 1:
                                ax = plt.axes()
                                ax.set_xscale("log")
                                ax.set_yscale("log")
                                ax.errorbar(Q, FullPolResults[Slice]['NSFAdd'], yerr=FullPolResults[Slice]['NSFUnc'], fmt = 'b*', label='NSF')
                                ax.errorbar(Q, FullPolResults[Slice]['NSFDiff'], yerr=FullPolResults[Slice]['NSFUnc'], fmt = 'g*', label='NSFDiff')
                                ax.errorbar(Q, FullPolResults[Slice]['SFAdd'], yerr=FullPolResults[Slice]['SFUnc'], fmt = 'r*', label='SF')
                            else:
                                plt.loglog(Q, FullPolResults[Slice]['NSFAdd'], 'b*', label='NSF')
                                plt.loglog(Q, FullPolResults[Slice]['NSFDiff'], 'g*', label='NSFDiff')
                                plt.loglog(Q, FullPolResults[Slice]['SFAdd'], 'r*', label='SF')
                            plt.xlabel('Q')
                            plt.ylabel('Intensity')
                            plt.title(Slice)
                            plt.legend()
                            plt.show()
                            '''
                            
    if 'Left' in sector_slices and 'Right' in sector_slices:
        Q_Left = FullPolResults['Left']['Q_Common']
        NSF_Left =  FullPolResults['Left']['NSFAdd']
        Q_Right = FullPolResults['Right']['Q_Common']
        NSF_Right =  FullPolResults['Right']['NSFAdd']
        fig = plt.figure()
        plt.loglog(Q_Left, NSF_Left, 'b*', label='NSF Left')
        plt.loglog(Q_Right, NSF_Right, 'm*', label='NSF Right')
        plt.xlabel('Q')
        plt.ylabel('Intensity')
        plt.title('Left and Right Slices')
        plt.legend()
        plt.show()

    if 'Top' in sector_slices and 'Bottom' in sector_slices:
        Q_Top = FullPolResults['Top']['Q_Common']
        NSF_Top =  FullPolResults['Top']['NSFAdd']
        Q_Bottom = FullPolResults['Bottom']['Q_Common']
        NSF_Bottom =  FullPolResults['Bottom']['NSFAdd']
        fig = plt.figure()
        plt.loglog(Q_Top, NSF_Top, 'b*', label='NSF Top')
        plt.loglog(Q_Bottom, NSF_Bottom, 'm*', label='NSF Bottom')
        plt.xlabel('Q')
        plt.ylabel('Intensity')
        plt.title('Top and Bottom Slices')
        plt.legend()
        plt.show()
        
        
        
                            
    '''
    if 'Vert' in sector_slices and 'Horz' in sector_slices:
        Matched_Vert = {}
        Matched_Vert['Q'] = [0]
        Matched_Vert['NSFADD'] = [0]
        Matched_Vert['NSFDIFF'] = [0]
        Matched_Vert['SFADD'] = [0]
        Vert_counter = 0
        for Q1 in FullPolResults['Vert']['Q_Common']:
            if Q1 in FullPolResults['Horz']['Q_Common']:
                Matched_Vert['Q'].append(FullPolResults['Vert']['Q_Common'][Vert_counter])
                Matched_Vert['NSFADD'].append(FullPolResults['Vert']['NSFAdd'][Vert_counter])
                Matched_Vert['NSFDIFF'].append(FullPolResults['Vert']['NSFDiff'][Vert_counter])
                Matched_Vert['SFADD'].append(FullPolResults['Vert']['SFAdd'][Vert_counter])
            Vert_counter += 1
            
        Matched_Horz = {}
        Matched_Horz['Q'] = [0]
        Matched_Horz['NSFADD'] = [0]
        Matched_Horz['NSFDIFF'] = [0]
        Matched_Horz['SFADD'] = [0]
        Horz_counter = 0
        for Q2 in FullPolResults['Horz']['Q_Common']:
            if Q2 in FullPolResults['Vert']['Q_Common']:
                Matched_Horz['Q'].append(FullPolResults['Horz']['Q_Common'][Horz_counter])
                Matched_Horz['NSFADD'].append(FullPolResults['Horz']['NSFAdd'][Horz_counter])
                Matched_Horz['NSFDIFF'].append(FullPolResults['Horz']['NSFDiff'][Horz_counter])
                Matched_Horz['SFADD'].append(FullPolResults['Horz']['SFAdd'][Horz_counter])
            Horz_counter += 1
            
        del Matched_Vert['Q'][0]
        del Matched_Vert['NSFADD'][0]
        del Matched_Vert['NSFDIFF'][0]
        del Matched_Vert['SFADD'][0]
        del Matched_Horz['Q'][0]
        del Matched_Horz['NSFADD'][0]
        del Matched_Horz['NSFDIFF'][0]
        del Matched_Horz['SFADD'][0]

        for i in range(0, len(Matched_Vert['Q'])):
            if Matched_Vert['Q'][i] != Matched_Horz['Q'][i]:
                if Matched_Vert['Q'][i] < Matched_Horz['Q'][i]:
                    j = i
                    while Matched_Vert['Q'][j] < Matched_Horz['Q'][i] and j < len(Matched_Vert['Q']):
                        del Matched_Vert['Q'][j]
                        del Matched_Vert['NSFADD'][j]
                        del Matched_Vert['NSFDIFF'][j]
                        del Matched_Vert['SFADD'][j]
                        j += 1
                elif Matched_Horz['Q'][i] < Matched_Vert['Q'][i]:
                    j = i
                    while Matched_Horz['Q'][j] < Matched_Vert['Q'][i] and j < len(Matched_Vert['Q']):
                        del Matched_Horz['Q'][j]
                        del Matched_Horz['NSFADD'][j]
                        del Matched_Horz['NSFDIFF'][j]
                        del Matched_Horz['SFADD'][j]
                        j += 1
                        
        print(len(Matched_Vert['Q']), len(Matched_Horz['Q']))

        Q = np.array(Matched_Vert['Q'])
        SF_Horz = np.array(Matched_Horz['SFADD'])
        SF_Vert = np.array(Matched_Vert['SFADD'])
        SF_Diff = SF_Horz - SF_Vert
        fig = plt.figure()
        #plt.semilogx(Q, SF_Horz, 'b*', label='SF_Horz')
        plt.loglog(Q, SF_Horz, 'b*', label='SF_Horz')
        plt.loglog(Q, SF_Vert, 'g*', label='SF_Vert')
        plt.xlabel('Q')
        plt.ylabel('Intensity')
        plt.title(Slice)
        plt.legend()
        plt.show()

        Nucl_Horz = np.array(Matched_Horz['NSFADD'])/2.0
        Nucl_Vert = np.array(Matched_Vert['NSFADD'])/2.0
        MParl_Diff = (np.array(Matched_Vert['NSFADD']) - np.array(Matched_Horz['NSFADD']))/2.0
        Marl_Div = np.power(np.array(Matched_Vert['NSFDIFF']),2) / (8.0*np.array(Matched_Horz['NSFADD']))
        fig = plt.figure()
        plt.loglog(Q, Nucl_Horz, 'r*', label='Nucl_Horz')
        plt.loglog(Q, Nucl_Vert, 'm*', label='Nucl_Vert')
        plt.loglog(Q, MParl_Diff, 'b*', label='MParl Diff Method')
        plt.loglog(Q, Marl_Div, 'g*', label='MParl Div Method')
        plt.xlabel('Q')
        plt.ylabel('Intensity')
        plt.title(Slice)
        plt.legend()
        plt.show()
        '''
        
                        
    

#*************************************************
#***           End of 'The Program'            ***
#*************************************************


