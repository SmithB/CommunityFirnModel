#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
2/24/2021

This script takes a pandas dataframe containing climate data for a particular
site and generates climate histories to feed into CFM as forcing.

The script resamples the data to the specified time step (e.g. if you have 
hourly data and you want a daily run, it resamples to daily.)

At present, spin up is generated by just repeatsing the reference climate 
interval over and over again.

YOU MAY HAVE TO EDIT THIS SCRIPT A LOT TO MAKE IT WORK WITH YOUR FILE STRUCTURE 
AND WHAT CLIMATE FILES YOU HAVE.

And, for now there are little things you need to search out and change manually,
like the reference climate interval. Sorry!

@author: maxstev
'''

import numpy as np
from datetime import datetime, timedelta, date
import pandas as pd
import time
import calendar
import hl_analytic as hla

def toYearFraction(date):
    '''
    convert datetime to decimal date 
    '''
    def sinceEpoch(date): # returns seconds since epoch
        return calendar.timegm(date.timetuple())
    s = sinceEpoch

    year = date.year
    startOfThisYear = datetime(year=year, month=1, day=1)
    startOfNextYear = datetime(year=year+1, month=1, day=1)

    yearElapsed = s(date) - s(startOfThisYear)
    yearDuration = s(startOfNextYear) - s(startOfThisYear)
    fraction = yearElapsed/yearDuration

    return date.year + fraction

def decyeartodatetime(din):
    start = din
    year = int(start)
    rem = start - year
    base = datetime(year, 1, 1)
    result = base + timedelta(seconds=(base.replace(year=base.year + 1) - base).total_seconds() * rem)
    result2 = result.replace(hour=0, minute=0, second=0, microsecond=0)
    return result

def effectiveT(T):
    '''
    The Arrhenius mean temperature.
    '''
    # Q   = -1 * 60.0e3
    Q   = -1 * 59500.0
    R   = 8.314
    k   = np.exp(Q/(R*T))
    km  = np.mean(k)
    return Q/(R*np.log(km))

def makeSpinFiles(CLIM_name,timeres='1D',Tinterp='mean',spin_date_st = 1980.0, spin_date_end = 1995.0,melt=False,desired_depth = None,SEB=False,rho_bottom=916):
    '''
    load a pandas dataframe, called df_CLIM, that will be resampled and then used 
    to create a time series of climate variables for spin up. 
    the index of must be datetimeindex for resampling.
    df_CLIM can have any number of columns: BDOT, TSKIN, SMELT, RAIN, 
    SUBLIM (use capital letters. We use SMELT because melt is a pandas function)
    Hopefully this makes it easy to adapt for the different climate products.

    UNITS FOR MASS FLUXES IN THE DATAFRAMES ARE kg/m^2 PER TIME STEP SIZE IN
    THE DATA FRAME. e.g. if you have hourly data in the dataframe, the units
    for accumulation are kg/m^2/hour - the mass of precip that fell during that 
    time interval.

    CFM takes units of m ice eq./year, so this script returns units in that 
    format.

    Parameters
    ----------

    timeres: pandas Timedelta (string)
        Resampling frequency, e.g. '1D' is 1 day; '1M' for 1 month.
    melt: boolean
        Whether or not the model run includes melt
    Tinterp: 'mean', 'effective', or 'weighted'
        how to resample the temperature; mean is regular mean, 'effective' is 
        Arrhenius mean; 'weighted' is accumulation-weighted mean
 	spin_date_st: float
 		decimal date of the start of the reference climate interval (RCI)
 	spin_date_end: float
 		decimal date of the end of the RCI

    Returns
    -------
    CD: dictionary
        Dictionary full of the inputs (time, SMB, temperature, etc.) that
        will force the CFM. Possible keys to have in the dictionary are: 'time',
        which is decimal date; 'TSKIN' (surface temperature), 'BDOT'
        (accumulation, m i.e.), 'SMELT' (snowmelt, m i.e.), and 'RAIN'. 
    StpsPerYr: float
        number of steps per year (mean) for the timeres you selected.
    depth_S1: float
        depth of the 550 kg m^-3 density horizon (or other density; you can pick)
        this is used for the regrid module
    depth_S2: float
        depth of the 750 kg m^-3 density horizon (or other density; you can pick)
        this is used for the regrid module
    desired_depth: float
        this is the depth you should set to be the bottom of the domain if you 
        want to model to 916 kg m^-3.
    '''

    SPY = 365.25*24*3600

    if type(CLIM_name) == str:
    	df_CLIM = pd.read_pickle(CLIM_name)
    else: #CLIM_name is not a pickle, it is the dataframe being passed
    	df_CLIM = CLIM_name

# <<<<<<< HEAD
    if not SEB:
        # drn = {'TS':'TSKIN'} #customize this to change your dataframe column names to match the required inputs
        # try:
        #     df_CLIM['RAIN'] = df_CLIM['PRECTOT'] - df_CLIM['PRECSNO']
        #     df_CLIM['BDOT'] = df_CLIM['PRECSNO'] + df_CLIM['EVAP']
        # except:
        #     pass
        # df_CLIM.rename(mapper=drn,axis=1,inplace=True)
        # try:
        #     df_CLIM.drop(['EVAP','PRECTOT','PRECSNO'],axis=1,inplace=True)
        # except:
        #     pass
        # l1 = df_CLIM.columns.values.tolist()
        # l2 = ['SMELT','BDOT','RAIN','TSKIN','SRHO']
        # notin = list(np.setdiff1d(l1,l2))
        # df_CLIM.drop(notin,axis=1,inplace=True)
        # # df_BDOT = pd.DataFrame(df_CLIM.BDOT)
        # df_TS = pd.DataFrame(df_CLIM.TSKIN)

        # res_dict_all = {'SMELT':'sum','BDOT':'sum','RAIN':'sum','TSKIN':'mean','SRHO':'mean'} # resample type for all possible variables
        # res_dict = {key:res_dict_all[key] for key in df_CLIM.columns} # resample type for just the data types in df_CLIM

        # # df_BDOT_re = df_BDOT.resample(timeres).sum()
        # if Tinterp == 'mean':
        #     df_TS_re = df_TS.resample(timeres).mean()
        # elif Tinterp == 'effective':
        #     df_TS_re = df_TS.resample(timeres).apply(effectiveT)
        # elif Tinterp == 'weighted':
        #     df_TS_re = pd.DataFrame(data=(df_BDOT.BDOT*df_TS.TSKIN).resample(timeres).sum()/(df_BDOT.BDOT.resample(timeres).sum()),columns=['TSKIN'])
        #     # pass

        # df_CLIM_re = df_CLIM.resample(timeres).agg(res_dict)
        # df_CLIM_re.TSKIN = df_TS_re.TSKIN
        # df_CLIM_ids = list(df_CLIM_re.columns)

        # df_CLIM_re['decdate'] = [toYearFraction(qq) for qq in df_CLIM_re.index]
        # df_CLIM_re = df_CLIM_re.fillna(method='pad')

        # # df_TS_re['decdate'] = [toYearFraction(qq) for qq in df_TS_re.index]
        # # df_BDOT_re['decdate'] = [toYearFraction(qq) for qq in df_BDOT_re.index]
        # # df_TS_re = df_TS_re.fillna(method='pad')

        # stepsperyear = 1/(df_CLIM_re.decdate.diff().mean())

        # BDOT_mean_IE = (df_CLIM_re['BDOT']*stepsperyear/917).mean()
        # T_mean = (df_TS_re['TSKIN']).mean()
        # print(BDOT_mean_IE)
        # print(T_mean)

        # hh  = np.arange(0,501)
        # age, rho = hla.hl_analytic(350,hh,T_mean,BDOT_mean_IE)    
        # if not desired_depth:
        #     desired_depth = hh[np.where(rho>=rho_bottom)[0][0]]
        #     depth_S1 = hh[np.where(rho>=550)[0][0]]
        #     depth_S2 = hh[np.where(rho>=750)[0][0]]
        # =======
        drn = {'TS':'TSKIN','EVAP':'SUBLIM'} #customize this to change your dataframe column names to match the required inputs
        try:
            df_CLIM['RAIN'] = df_CLIM['PRECTOT'] - df_CLIM['PRECSNO']
            df_CLIM['BDOT'] = df_CLIM['PRECSNO'] #+ df_CLIM['EVAP']
            # df_CLIM['SUBLIM'] = df_CLIM[]

        except:
            pass
        df_CLIM.rename(mapper=drn,axis=1,inplace=True)
        try:
            df_CLIM.drop(['EVAP','PRECTOT','PRECSNO'],axis=1,inplace=True)
        except:
            pass
        l1 = df_CLIM.columns.values.tolist()
        l2 = ['SMELT','BDOT','RAIN','TSKIN','SUBLIM','SRHO']
        notin = list(np.setdiff1d(l1,l2))
        df_CLIM.drop(notin,axis=1,inplace=True)
        # df_BDOT = pd.DataFrame(df_CLIM.BDOT)
        df_TS = pd.DataFrame(df_CLIM.TSKIN)

        res_dict_all = {'SMELT':'sum','BDOT':'sum','RAIN':'sum','TSKIN':'mean','SUBLIM':'sum','SRHO':'mean'} # resample type for all possible variables
        res_dict = {key:res_dict_all[key] for key in df_CLIM.columns} # resample type for just the data types in df_CLIM

        # df_BDOT_re = df_BDOT.resample(timeres).sum()
        if Tinterp == 'mean':
            df_TS_re = df_TS.resample(timeres).mean()
        elif Tinterp == 'effective':
            df_TS_re = df_TS.resample(timeres).apply(effectiveT)
        elif Tinterp == 'weighted':
            df_TS_re = pd.DataFrame(data=(df_BDOT.BDOT*df_TS.TSKIN).resample(timeres).sum()/(df_BDOT.BDOT.resample(timeres).sum()),columns=['TSKIN'])
            # pass

        df_CLIM_re = df_CLIM.resample(timeres).agg(res_dict)
        df_CLIM_re.TSKIN = df_TS_re.TSKIN
        df_CLIM_ids = list(df_CLIM_re.columns)

        df_CLIM_re['decdate'] = [toYearFraction(qq) for qq in df_CLIM_re.index]
        df_CLIM_re = df_CLIM_re.fillna(method='pad')

        # df_TS_re['decdate'] = [toYearFraction(qq) for qq in df_TS_re.index]
        # df_BDOT_re['decdate'] = [toYearFraction(qq) for qq in df_BDOT_re.index]
        # df_TS_re = df_TS_re.fillna(method='pad')

        stepsperyear = 1/(df_CLIM_re.decdate.diff().mean())


        if 'SUBLIM' not in df_CLIM_re:
            df_CLIM_re['SUBLIM'] = np.zeros_like(df_CLIM_re['BDOT'])
            print('SUBLIM not in df_CLIM! (RCMpkl_to_spin.py, 232')

        BDOT_mean_IE = ((df_CLIM_re['BDOT']+df_CLIM_re['SUBLIM'])*stepsperyear/917).mean()
        T_mean = (df_TS_re['TSKIN']).mean()
        print(BDOT_mean_IE)
        print(T_mean)

        hh  = np.arange(0,501)
        age, rho = hla.hl_analytic(350,hh,T_mean,BDOT_mean_IE)    
        if not desired_depth:
            # desired_depth = hh[np.where(rho>=916)[0][0]]
            desired_depth = hh[np.where(rho>=rho_bottom)[0][0]]
            depth_S1 = hh[np.where(rho>=450)[0][0]]
            depth_S2 = hh[np.where(rho>=650)[0][0]]
        else:
            desired_depth = desired_depth
            depth_S1 = desired_depth * 0.5
            depth_S2 = desired_depth * 0.75
        
        # #### Make spin up series ###
        # RCI_length = spin_date_end-spin_date_st+1
        # num_reps = int(np.round(desired_depth/BDOT_mean_IE/RCI_length))
        # years = num_reps*RCI_length
        # sub = np.arange(-1*years,0,RCI_length)
        # startyear = int(df_CLIM_re.index[0].year + sub[0])
        # startmonth = df_CLIM_re.index[0].month
        # startday  = df_CLIM_re.index[0].day
        # startstring = '{}/{}/{}'.format(startday,startmonth,startyear)

        # msk = df_CLIM_re.decdate.values<spin_date_end+1
        # spin_days = df_CLIM_re.decdate.values[msk]

        # smb_spin = df_CLIM_re['BDOT'][msk].values
        # tskin_spin = df_CLIM_re['TSKIN'][msk].values

        # nu = len(spin_days)
        # spin_days_all = np.zeros(len(sub)*nu)
        # smb_spin_all = np.zeros_like(spin_days_all)
        # tskin_spin_all = np.zeros_like(spin_days_all)

        # spin_days_all = (sub[:,np.newaxis]+spin_days).flatten()
        # spin_dict = {}
        # for ID in df_CLIM_ids:
        #     spin_dict[ID] = np.tile(df_CLIM_re[ID][msk].values, len(sub))
        # # print(spin_days_all[0])

        # df_CLIM_decdate = df_CLIM_re.set_index('decdate')
        # df_spin = pd.DataFrame(spin_dict,index = spin_days_all)
        # df_spin.index.name = 'decdate'

        # df_FULL = pd.concat([df_spin,df_CLIM_decdate])
        # print('df_full:',df_FULL.head())

        # CD = {}
        # CD['time'] = df_FULL.index
        # for ID in df_CLIM_ids:
        #     if ID == 'TSKIN':
        #         CD[ID] = df_FULL[ID].values
        # >>>>>>> master
        # else:
        #     desired_depth = desired_depth
        #     depth_S1 = desired_depth * 0.5
        #     depth_S2 = desired_depth * 0.75
        
        #### Make spin up series ###
        RCI_length = spin_date_end-spin_date_st+1
        num_reps = int(np.round(desired_depth/BDOT_mean_IE/RCI_length))
        years = num_reps*RCI_length
        sub = np.arange(-1*years,0,RCI_length)
        startyear = int(df_CLIM_re.index[0].year + sub[0])
        startmonth = df_CLIM_re.index[0].month
        startday  = df_CLIM_re.index[0].day
        startstring = '{}/{}/{}'.format(startday,startmonth,startyear)

        msk = df_CLIM_re.decdate.values<spin_date_end+1
        spin_days = df_CLIM_re.decdate.values[msk]

        smb_spin = df_CLIM_re['BDOT'][msk].values
        tskin_spin = df_CLIM_re['TSKIN'][msk].values

        nu = len(spin_days)
        spin_days_all = np.zeros(len(sub)*nu)
        smb_spin_all = np.zeros_like(spin_days_all)
        tskin_spin_all = np.zeros_like(spin_days_all)

        spin_days_all = (sub[:,np.newaxis]+spin_days).flatten()
        spin_dict = {}
        for ID in df_CLIM_ids:
            spin_dict[ID] = np.tile(df_CLIM_re[ID][msk].values, len(sub))
        # print(spin_days_all[0])

        df_CLIM_decdate = df_CLIM_re.set_index('decdate')
        df_spin = pd.DataFrame(spin_dict,index = spin_days_all)
        df_spin.index.name = 'decdate'

        df_FULL = pd.concat([df_spin,df_CLIM_decdate])
        print('df_full (no seb):',df_FULL.head())

        CD = {}
        CD['time'] = df_FULL.index
        for ID in df_CLIM_ids:
            if ID == 'TSKIN':
                CD[ID] = df_FULL[ID].values
            elif ID=='SRHO':
                CD[ID] = df_FULL[ID].values
            else:
                CD[ID] = df_FULL[ID].values * stepsperyear / 917

    ##############################################
    ##############################################

    else: #SEB True
        l1 = df_CLIM.columns.values.tolist()

        if 'SMELT' in l1:
            df_CLIM.drop(['SMELT'],axis=1,inplace=True)

        # df_TS = pd.DataFrame(df_CLIM.TSKIN)

        # res_dict_all = ({'SMELT':'sum','BDOT':'sum','RAIN':'sum','TSKIN':'mean','T2m':'mean',
        #                'ALBEDO':'mean','QL':'mean','QH':'mean','SUBLIM':'sum','SW_d':'mean'}) # resample type for all possible variables
        
        # res_dict_all = ({'BDOT':'sum','RAIN':'sum','TSKIN':'mean','T2m':'mean',
        #                'ALBEDO':'mean','QL':'sum','QH':'sum','SUBLIM':'sum','SW_d':'sum','LW_d':'sum'}) # resample type for all possible variables

        res_dict_all = ({'BDOT':'sum','RAIN':'sum','TSKIN':'mean','T2m':'mean',
                       'ALBEDO':'mean','QL':'mean','QH':'mean','SUBLIM':'sum','SW_d':'mean','LW_d':'mean','LW_u':'mean'}) # resample type for all possible variables

        res_dict = {key:res_dict_all[key] for key in df_CLIM.columns} # resample type for just the data types in df_CLIM

        df_CLIM_re = df_CLIM.resample(timeres).agg(res_dict)
        df_CLIM_ids = list(df_CLIM_re.columns)

        df_CLIM_re['decdate'] = [toYearFraction(qq) for qq in df_CLIM_re.index]
        df_CLIM_re = df_CLIM_re.fillna(method='pad')

        stepsperyear = 1/(df_CLIM_re.decdate.diff().mean())

        BDOT_mean_IE = (df_CLIM_re['BDOT']*stepsperyear/917).mean()
        
        try:
            T_mean = (df_CLIM_re['TSKIN']).mean()
        except:
            T_mean = (df_CLIM_re['T2m']).mean()
        print(BDOT_mean_IE)
        print(T_mean)

        hh  = np.arange(0,501)
        age, rho = hla.hl_analytic(350,hh,T_mean,BDOT_mean_IE)    
        if not desired_depth:
            desired_depth = hh[np.where(rho>=rho_bottom)[0][0]]
            depth_S1 = hh[np.where(rho>=550)[0][0]]
            depth_S2 = hh[np.where(rho>=750)[0][0]]
        else:
            desired_depth = desired_depth
            depth_S1 = desired_depth * 0.5
            depth_S2 = desired_depth * 0.75

        #### Make spin up series ###
        RCI_length = spin_date_end-spin_date_st+1
        num_reps = int(np.round(desired_depth/BDOT_mean_IE/RCI_length))
        years = num_reps*RCI_length
        sub = np.arange(-1*years,0,RCI_length)
        startyear = int(df_CLIM_re.index[0].year + sub[0])
        startmonth = df_CLIM_re.index[0].month
        startday  = df_CLIM_re.index[0].day
        startstring = '{}/{}/{}'.format(startday,startmonth,startyear)

        msk = df_CLIM_re.decdate.values<spin_date_end+1
        spin_days = df_CLIM_re.decdate.values[msk]

        # smb_spin = df_CLIM_re['BDOT'][msk].values
        # tskin_spin = df_CLIM_re['TSKIN'][msk].values

        nu = len(spin_days)
        spin_days_all = np.zeros(len(sub)*nu)

        spin_days_all = (sub[:,np.newaxis]+spin_days).flatten()
        spin_dict = {}
        for ID in df_CLIM_ids:
            spin_dict[ID] = np.tile(df_CLIM_re[ID][msk].values, len(sub))
        # print(spin_days_all[0])

        df_CLIM_decdate = df_CLIM_re.set_index('decdate')
        df_spin = pd.DataFrame(spin_dict,index = spin_days_all)
        df_spin.index.name = 'decdate'

        df_FULL = pd.concat([df_spin,df_CLIM_decdate])
        print('df_full:',df_FULL.head())

        CD = {}
        CD['time'] = df_FULL.index
        massIDs = ['SMELT','BDOT','RAIN','SUBLIM','EVAP']
        for ID in df_CLIM_ids:
            if ID not in massIDs:
                CD[ID] = df_FULL[ID].values            
            else:
                CD[ID] = df_FULL[ID].values * stepsperyear / 917

    return CD, stepsperyear, depth_S1, depth_S2, desired_depth
