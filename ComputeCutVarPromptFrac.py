'''
python script for the computation of the prompt / non-prompt fraction with the cut-variation method
run: python ComputeCutVarPromptFrac.py cfgFileName.yml outFileName.root
'''

import sys
import argparse
import os
from itertools import product
import numpy as np
import yaml
from ROOT import TFile, TH1F, TH2F, TCanvas, TLegend, TGraphAsymmErrors, TLatex, gRandom, TF1  # pylint: disable=import-error,no-name-in-module
from ROOT import kBlack, kRed, kAzure, kGreen, kRainBow # pylint: disable=import-error,no-name-in-module
from ROOT import kFullCircle, kFullSquare, kOpenSquare, kOpenCircle, kOpenCross, kOpenDiamond # pylint: disable=import-error,no-name-in-module
from utils.AnalysisUtils import GetPromptFDFractionFc, GetFractionNb
from utils.AnalysisUtils import GetPromptFDYieldsAnalyticMinimisation, ApplyVariationToList
from utils.ReadModel import ReadTAMU, ReadPHSD, ReadMCatsHQ, ReadCatania
from utils.StyleFormatter import SetGlobalStyle, SetObjectStyle

parser = argparse.ArgumentParser(description='Arguments to pass')
parser.add_argument('cfgFileName', metavar='text', default='cfgFileName.yml',
                    help='config file name with root input files')
parser.add_argument('outFileName', metavar='text', default='outFile.root',
                    help='output root file name')
args = parser.parse_args()

outFileNameEffPDF = args.outFileName.replace('.root', '_Eff.pdf')
outFileNameDistrPDF = args.outFileName.replace('.root', '_Distr.pdf')
outFileNameFracPDF = args.outFileName.replace('.root', '_Frac.pdf')
outFileNameCorrMatrixPDF = args.outFileName.replace('.root', '_CorrMatrix.pdf')

with open(args.cfgFileName, 'r') as ymlCutSetFile:
    cutSetCfg = yaml.load(ymlCutSetFile, yaml.FullLoader)

inputFilesRaw = cutSetCfg['rawyields']['inputfiles']
inputFilesEff = cutSetCfg['efficiencies']['inputfiles']
inputFilesBkg = cutSetCfg['background']['inputfiles']
if inputFilesBkg is None:
    inputFilesBkg = inputFilesRaw.copy()

inputDirRaw = cutSetCfg['rawyields']['inputdir']
inputDirEff = cutSetCfg['efficiencies']['inputdir']
inputDirBkg = cutSetCfg['background']['inputdir']

histoNameRaw = cutSetCfg['rawyields']['histoname']
histoNameEffPrompt = cutSetCfg['efficiencies']['histonames']['prompt']
histoNameEffFD = cutSetCfg['efficiencies']['histonames']['feeddown']
histoNameBkg = cutSetCfg['background']['histoname']

nSets = len(cutSetCfg['rawyields']['inputfiles'])

doRawYieldsSmearing = cutSetCfg['minimisation']['doRawYieldSmearing']

applyEffVariation = cutSetCfg['minimisation']['applyEffVariation']['enable']
relEffVariation = cutSetCfg['minimisation']['applyEffVariation']['relvariation']
effVariationOpt = cutSetCfg['minimisation']['applyEffVariation']['option']
applyEffVarToPrompt = cutSetCfg['minimisation']['applyEffVariation']['prompt']
applyEffVarToFD = cutSetCfg['minimisation']['applyEffVariation']['feeddown']

if nSets != len(cutSetCfg['efficiencies']['inputfiles']):
    print('ERROR: number or raw yield files and efficiency files not consistent! Please check your config file. Exit')
    sys.exit()

hRawYields, hEffPrompt, hEffFD, hEv, hBkg = [], [], [], [], []

# load RAA
RaaPrompt_config = cutSetCfg['theorydriven']['predictions']['Raa']['prompt']
if not isinstance(RaaPrompt_config, float) and not isinstance(RaaPrompt_config, int):
    if not isinstance(RaaPrompt_config, str):
        print('ERROR: RAA must be at least a string or a number. Exit')
        sys.exit()
    else:
        Raa_model_name = cutSetCfg['theorydriven']['predictions']['Raa']['model']
        if Raa_model_name not in ['phsd', 'Catania', 'tamu', 'MCatsHQ']:
            print('ERROR: wrong model name, please check the list of avaliable models. Exit')
            sys.exit()
        else:
            if Raa_model_name == 'phsd':
                RaaPromptSpline, _, ptMinRaaPrompt, ptMaxRaaPrompt = ReadPHSD(RaaPrompt_config)
            elif Raa_model_name == 'Catania':
                RaaPromptSpline, _, ptMinRaaPrompt, ptMaxRaaPrompt = ReadCatania(RaaPrompt_config)
            elif Raa_model_name == 'MCatsHQ':
                RaaPromptSpline, _, ptMinRaaPrompt, ptMaxRaaPrompt = ReadMCatsHQ(RaaPrompt_config)
            elif Raa_model_name == 'tamu':
                RaaPromptSpline, _, ptMinRaaPrompt, ptMaxRaaPrompt = ReadTAMU(RaaPrompt_config)
else:
    RaaPrompt = RaaPrompt_config

RaaFD_config = cutSetCfg['theorydriven']['predictions']['Raa']['feeddown']
if not isinstance(RaaFD_config, float) and not isinstance(RaaFD_config, int):
    if not isinstance(RaaFD_config, str):
        print('ERROR: RAA must be at least a string or a number. Exit')
        sys.exit()
    else:
        Raa_model_name = cutSetCfg['theorydriven']['predictions']['Raa']['model']
        if Raa_model_name not in ['phsd', 'Catania', 'tamu', 'MCatsHQ']:
            print('ERROR: wrong model name, please check the list of avaliable models. Exit')
            sys.exit()
        else:
            if Raa_model_name == 'phsd':
                RaaFDSpline, _, ptMinRaaFD, ptMaxRaaFD = ReadPHSD(RaaFD_config)
            elif Raa_model_name == 'Catania':
                RaaFDSpline, _, ptMinRaaFD, ptMaxRaaFD = ReadCatania(RaaFD_config)
            elif Raa_model_name == 'MCatsHQ':
                RaaFDSpline, _, ptMinRaaFD, ptMaxRaaFD = ReadMCatsHQ(RaaFD_config)
            elif Raa_model_name == 'tamu':
                RaaFDSpline, _, ptMinRaaFD, ptMaxRaaFD = ReadTAMU(RaaFD_config)
else:
    RaaFD = RaaFD_config

# load inputs for theory-driven methods
compareToFc = cutSetCfg['theorydriven']['enableFc']
compareToNb = cutSetCfg['theorydriven']['enableNb']
hCrossSecPrompt, hCrossSecFD = [], []

for inFileNameRawYield, inFileNameEff, inFileNameBkg in zip(inputFilesRaw, inputFilesEff, inputFilesBkg):
    inFileNameRawYield = os.path.join(inputDirRaw, inFileNameRawYield)
    inFileRawYield = TFile.Open(inFileNameRawYield)
    hRawYields.append(inFileRawYield.Get(histoNameRaw))
    hRawYields[-1].SetDirectory(0)
    if compareToNb:
        hEv.append(inFileRawYield.Get('hEvForNorm'))
        hEv[-1].SetDirectory(0)
    inFileNameEff = os.path.join(inputDirEff, inFileNameEff)
    inFileEff = TFile.Open(inFileNameEff)
    hEffPrompt.append(inFileEff.Get(histoNameEffPrompt))
    hEffFD.append(inFileEff.Get(histoNameEffFD))
    hEffPrompt[-1].SetDirectory(0)
    hEffFD[-1].SetDirectory(0)
    if inputDirBkg is not None and inFileNameBkg is not None:
        inFileNameBkg = os.path.join(inputDirBkg, inFileNameBkg)
        inFileBkg = TFile.Open(inFileNameBkg)
        hBkg.append(inFileBkg.Get(histoNameBkg))
        hBkg[-1].SetDirectory(0)

if compareToFc or compareToNb:
    crossSecCfg = cutSetCfg['theorydriven']['predictions']['crosssec']
    inFileCrossSec = TFile.Open(crossSecCfg['inputfile'])
    hCrossSecPrompt.append(inFileCrossSec.Get(f"{crossSecCfg['histonames']['prompt']}_central"))
    hCrossSecPrompt.append(inFileCrossSec.Get(f"{crossSecCfg['histonames']['prompt']}_min"))
    hCrossSecPrompt.append(inFileCrossSec.Get(f"{crossSecCfg['histonames']['prompt']}_max"))
    hCrossSecFD.append(inFileCrossSec.Get(f"{crossSecCfg['histonames']['feeddown']}_central_corr"))
    hCrossSecFD.append(inFileCrossSec.Get(f"{crossSecCfg['histonames']['feeddown']}_min_corr"))
    hCrossSecFD.append(inFileCrossSec.Get(f"{crossSecCfg['histonames']['feeddown']}_max_corr"))
    if compareToNb:
        sigmaMB = cutSetCfg['theorydriven']['sigmaMB']

SetGlobalStyle(padleftmargin=0.15, padtopmargin=0.08, titleoffsetx=1.,
               titleoffsety=1.4, opttitle=1, palette=kRainBow, maxdigits=2)

legDistr = TLegend(0.45, 0.69, 0.75, 0.89)
legDistr.SetFillStyle(0)
legDistr.SetBorderSize(0)
legDistr.SetTextSize(0.045)

legEff = TLegend(0.2, 0.2, 0.4, 0.4)
legEff.SetFillStyle(0)
legEff.SetBorderSize(0)
legEff.SetTextSize(0.045)

legFrac = TLegend(0.2, 0.79, 0.4, 0.89)
legFrac.SetFillStyle(0)
legFrac.SetBorderSize(0)
legFrac.SetTextSize(0.045)

latInfo = TLatex()
latInfo.SetNDC()
latInfo.SetTextSize(0.045)
latInfo.SetTextFont(42)
latInfo.SetTextColor(1)

hCorrYieldPrompt = hRawYields[0].Clone('hCorrYieldPrompt')
hCorrYieldPrompt.SetTitle(';#it{p}_{T} (GeV/#it{c}); #it{N}_{prompt}')
SetObjectStyle(hCorrYieldPrompt, color=kRed+1, fillcolor=kRed+1, markerstyle=kFullCircle)

hCorrYieldFD = hRawYields[0].Clone('hCorrYieldFD')
hCorrYieldFD.SetTitle(';#it{p}_{T} (GeV/#it{c}); #it{N}_{non-prompt}')
SetObjectStyle(hCorrYieldFD, color=kAzure+4, fillcolor=kAzure+4, markerstyle=kFullSquare)

hCovCorrYields = [[hRawYields[0].Clone('hCovPromptPrompt'), hRawYields[0].Clone('hCovPromptFD')],
                  [hRawYields[0].Clone('hCovFDPrompt'), hRawYields[0].Clone('hCovFDFD')]]
for iRow, row in enumerate(hCovCorrYields):
    for iCol, hCov in enumerate(row):
        SetObjectStyle(hCov, linecolor=kBlack)
        if iRow == 0:
            rowName = '#it{N}_{prompt}'
        else:
            rowName = '#it{N}_{non-prompt}'
        if iCol == 0:
            colName = '#it{N}_{prompt}'
        else:
            colName = '#it{N}_{non-prompt}'
        hCov.SetTitle(f';#it{{p}}_{{T}} (GeV/#it{{c}}); #sigma({rowName}, {colName})')

hRawYieldsVsCut, hRawYieldsVsCutReSum, hRawYieldPromptVsCut, hRawYieldFDVsCut, cDistr = [], [], [], [], []
hEffPromptVsCut, hEffFDVsCut, cEff = [], [], []
hPromptFracVsCut, hFDFracVsCut, gPromptFracFcVsCut, gFDFracFcVsCut, gPromptFracNbVsCut, \
    gFDFracNbVsCut, cFrac = [], [], [], [], [], [], []
hCorrMatrixCutSets, cCorrMatrix = [], []

if cutSetCfg['linearplot']['enable']:
    fNfdNprompt = []
    cLinearPlot = []
    legendLinearPlot = []
    if cutSetCfg['linearplot']['uncbands']:
        fNfdNpromptUpper = []
        fNfdNpromptLower = []

for iPt in range(hRawYields[0].GetNbinsX()):
    ptMin = hRawYields[0].GetBinLowEdge(iPt+1)
    ptMax = ptMin + hRawYields[0].GetBinWidth(iPt+1)

    listRawYield = [hRaw.GetBinContent(iPt+1) for hRaw in hRawYields]
    listRawYieldUnc = [hRaw.GetBinError(iPt+1) for hRaw in hRawYields]
    listEffPrompt = [hEffP.GetBinContent(iPt+1) for hEffP in hEffPrompt]
    listEffPromptUnc = [hEffP.GetBinError(iPt+1) for hEffP in hEffPrompt]
    listEffFD = [hEffF.GetBinContent(iPt+1) for hEffF in hEffFD]
    listEffFDUnc = [hEffF.GetBinError(iPt+1) for hEffF in hEffFD]
    listBkg = [hbkg.GetBinContent(iPt+1) for hbkg in hBkg]
    listBkgUnc = [hbkg.GetBinError(iPt+1) for hbkg in hBkg]

    if cutSetCfg['linearplot']['enable']:
        fNfdNprompt.append([])
        cLinearPlot.append(TCanvas(f'LinearPlot_Pt{iPt+1}-{iPt+2}', '', 800, 800))
        cLinearPlot[iPt].SetTitle(f'LinearPlot_Pt{iPt+1}-{iPt+2}')
        legendLinearPlot.append(TLegend(0.6, 0.6, 0.9, 0.9))
        legendLinearPlot[iPt].SetNColumns(3)
        if cutSetCfg['linearplot']['uncbands']:
            fNfdNpromptUpper.append([])
            fNfdNpromptLower.append([])

    # apply smearing to raw yields
    if doRawYieldsSmearing:
        listRawYield.reverse()
        listRawYieldSmeared = []
        listBkg.reverse()
        listDelta = []
        listDeltaSmeared = []
        listDeltaBkg = []
        listDeltaSmearedBkg = []
        if cutSetCfg['minimisation']['setseed']:
            gRandom.SetSeed(10)
        for iRawYeld, _ in enumerate(listRawYield):
            if iRawYeld == 0:
                listDelta.append(0.)
                listDeltaBkg.append(0.)
            else:
                listDelta.append(listRawYield[iRawYeld] - listRawYield[iRawYeld-1])
                listDeltaBkg.append(listBkg[iRawYeld] - listBkg[iRawYeld-1])
            listDeltaSmeared.append(gRandom.PoissonD(listDelta[iRawYeld] + listDeltaBkg[iRawYeld]))
            if cutSetCfg['minimisation']['correlated']:
                if iRawYeld == 0:
                    listRawYieldSmeared.append(gRandom.PoissonD(listRawYield[iRawYeld] + listBkg[iRawYeld])
                                               - listBkg[iRawYeld])
                else:
                    listRawYieldSmeared.append(listRawYieldSmeared[iRawYeld-1] + listDeltaSmeared[iRawYeld]
                                               - listDeltaBkg[iRawYeld])
            else:
                listRawYieldSmeared.append(gRandom.PoissonD(listRawYield[iRawYeld]))
        listRawYieldSmeared.reverse()
        listRawYield = listRawYieldSmeared

    # apply variation to efficiency
    if applyEffVariation:
        if applyEffVarToPrompt:
            listEffPrompt = ApplyVariationToList(listEffPrompt, relEffVariation, effVariationOpt)
        if applyEffVarToFD:
            listEffFD = ApplyVariationToList(listEffFD, relEffVariation, effVariationOpt)

    corrYields, covMatrixCorrYields, chiSquare, matrices = \
        GetPromptFDYieldsAnalyticMinimisation(listEffPrompt, listEffFD, listRawYield, listEffPromptUnc, listEffFDUnc,
                                              listRawYieldUnc, cutSetCfg['minimisation']['correlated'])

    hCorrYieldPrompt.SetBinContent(iPt+1, corrYields.item(0))
    hCorrYieldPrompt.SetBinError(iPt+1, np.sqrt(covMatrixCorrYields.item(0, 0)))
    hCorrYieldFD.SetBinContent(iPt+1, corrYields.item(1))
    hCorrYieldFD.SetBinError(iPt+1, np.sqrt(covMatrixCorrYields.item(1, 1)))
    for covElem in product(range(2), range(2)):
        hCovCorrYields[covElem[0]][covElem[1]].SetBinContent(iPt+1, covMatrixCorrYields.item(covElem))
        hCovCorrYields[covElem[0]][covElem[1]].SetBinError(iPt+1, 0.)

    ptString = f'pT{ptMin:.0f}_{ptMax:.0f}'
    commonString = f'{ptMin:.0f} < #it{{p}}_{{T}} < {ptMax:.0f}  GeV/#it{{c}};cut set'
    hRawYieldsVsCut.append(TH1F(f'hRawYieldsVsCutPt_{ptString}', f'{commonString};raw yield', nSets, 0.5, nSets + 0.5))
    hRawYieldsVsCutReSum.append(TH1F(f'hRawYieldsVsCutReSum_{ptString}', f'{commonString};raw yield',
                                     nSets, 0.5, nSets + 0.5))
    hRawYieldPromptVsCut.append(TH1F(f'hRawYieldPromptVsCut_{ptString}', f'{commonString};raw yield',
                                     nSets, 0.5, nSets + 0.5))
    hRawYieldFDVsCut.append(TH1F(f'hRawYieldFDVsCut_{ptString}', f'{commonString};raw yield', nSets, 0.5, nSets + 0.5))
    hEffPromptVsCut.append(TH1F(f'hEffPromptVsCut_{ptString}', f'{commonString};efficiency', nSets, 0.5, nSets + 0.5))
    hEffFDVsCut.append(TH1F(f'hEffFDVsCut_{ptString}', f'{commonString};efficiency', nSets, 0.5, nSets + 0.5))
    hPromptFracVsCut.append(TH1F(f'hPromptFracVsCut_{ptString}', f'{commonString};#it{{f}}_{{prompt}}',
                                 nSets, 0.5, nSets + 0.5))
    hFDFracVsCut.append(TH1F(f'hFDFracVsCut_{ptString}', f'{commonString};#it{{f}}_{{FD}}', nSets, 0.5, nSets + 0.5))

    SetObjectStyle(hRawYieldsVsCut[iPt], linecolor=kBlack, markercolor=kBlack, markerstyle=kFullCircle)
    SetObjectStyle(hRawYieldPromptVsCut[iPt], color=kRed+1, fillcolor=kRed+1, markerstyle=kOpenCircle, fillalpha=0.3)
    SetObjectStyle(hRawYieldFDVsCut[iPt], color=kAzure+4, fillcolor=kAzure+4, markerstyle=kOpenSquare, fillalpha=0.3)
    SetObjectStyle(hRawYieldsVsCutReSum[iPt], linecolor=kGreen+2)
    SetObjectStyle(hEffPromptVsCut[iPt], color=kRed+1, markerstyle=kFullCircle)
    SetObjectStyle(hEffFDVsCut[iPt], color=kAzure+4, markerstyle=kFullSquare)
    SetObjectStyle(hPromptFracVsCut[iPt], color=kRed+1, markerstyle=kFullCircle)
    SetObjectStyle(hFDFracVsCut[iPt], color=kAzure+4, markerstyle=kFullSquare)

    hCorrMatrixCutSets.append(TH2F(f'hCorrMatrixCutSets_{ptString}', f'{commonString};cut set',
                                   nSets, 0.5, nSets + 0.5, nSets, 0.5, nSets + 0.5))
    for mEl in product(range(nSets), range(nSets)):
        hCorrMatrixCutSets[iPt].SetBinContent(mEl[0]+1, mEl[1]+1, matrices['corrMatrix'].item(mEl[0], mEl[1]))

    # cross sections from theory if comparison enabled
    if compareToFc or compareToNb:
        crossSecPrompt = [h.Integral(h.GetXaxis().FindBin(ptMin*1.0001), h.GetXaxis().FindBin(ptMax*0.9999), 'width') /
                          (ptMax - ptMin) for h in hCrossSecPrompt]
        crossSecFD = [h.Integral(h.GetXaxis().FindBin(ptMin*1.0001), h.GetXaxis().FindBin(ptMax*0.9999), 'width') /
                      (ptMax - ptMin) for h in hCrossSecFD]

        if compareToFc:
            gPromptFracFcVsCut.append(TGraphAsymmErrors(nSets))
            gPromptFracFcVsCut[iPt].SetNameTitle(f'gPromptFracFcVsCut_{ptString}',
                                                 f'{commonString};#it{{f}}_{{prompt}}')
            gFDFracFcVsCut.append(TGraphAsymmErrors(nSets))
            gFDFracFcVsCut[iPt].SetNameTitle(f'gFDFracFcVsCut_{ptString}', f'{commonString};#it{{f}}_{{FD}}')
            SetObjectStyle(gPromptFracFcVsCut[iPt], color=kRed+3, fillalpha=0.3, markerstyle=kOpenCircle, markersize=2.)
            SetObjectStyle(gFDFracFcVsCut[iPt], color=kAzure+3, fillalpha=0.3, markerstyle=kOpenSquare, markersize=2.)

        if compareToNb:
            gPromptFracNbVsCut.append(TGraphAsymmErrors(nSets))
            gPromptFracNbVsCut[iPt].SetNameTitle(f'gPromptFracNbVsCut_{ptString}',
                                                 f'{commonString};#it{{f}}_{{prompt}}')
            gFDFracNbVsCut.append(TGraphAsymmErrors(nSets))
            gFDFracNbVsCut[iPt].SetNameTitle(f'gFDFracNbVsCut_{ptString}', f'{commonString};#it{{f}}_{{FD}}')
            SetObjectStyle(gPromptFracNbVsCut[iPt], color=kRed-7, markerstyle=kOpenDiamond, markersize=3.)
            SetObjectStyle(gFDFracNbVsCut[iPt], color=kAzure+5, markerstyle=kOpenCross, markersize=2.)

    for iCutSet, (rawY, effP, effF, rawYunc, effPunc, effFunc) in enumerate(zip(listRawYield, listEffPrompt, listEffFD,
                                                                                listRawYieldUnc, listEffPromptUnc,
                                                                                listEffFDUnc)):
        # efficiency
        hEffPromptVsCut[iPt].SetBinContent(iCutSet+1, effP)
        hEffPromptVsCut[iPt].SetBinError(iCutSet+1, effPunc)
        hEffFDVsCut[iPt].SetBinContent(iCutSet+1, effF)
        hEffFDVsCut[iPt].SetBinError(iCutSet+1, effFunc)

        # raw yields (including prompt and non-prompt raw yields)
        hRawYieldsVsCut[iPt].SetBinContent(iCutSet+1, rawY)
        hRawYieldsVsCut[iPt].SetBinError(iCutSet+1, rawYunc)
        hRawYieldPromptVsCut[iPt].SetBinContent(iCutSet+1, corrYields.item(0) * effP)
        hRawYieldPromptVsCut[iPt].SetBinError(iCutSet+1, np.sqrt(covMatrixCorrYields.item(0, 0)) * effP)
        hRawYieldFDVsCut[iPt].SetBinContent(iCutSet+1, corrYields.item(1) * effF)
        hRawYieldFDVsCut[iPt].SetBinError(iCutSet+1, np.sqrt(covMatrixCorrYields.item(1, 1)) * effF)
        hRawYieldsVsCutReSum[iPt].SetBinContent(iCutSet+1, hRawYieldPromptVsCut[iPt].GetBinContent(iCutSet+1) +
                                                hRawYieldFDVsCut[iPt].GetBinContent(iCutSet+1))

        if cutSetCfg['linearplot']['enable']:
            fNfdNprompt[iPt].append(TF1(f'cutset{iCutSet+1}', '[1]*x + [0]', 0., max(corrYields)/2.))
            fNfdNprompt[iPt][iCutSet].SetParameter(0, rawY/effP)
            fNfdNprompt[iPt][iCutSet].SetParameter(1, -effF/effP)
            if cutSetCfg['linearplot']['uncbands']:
                fNfdNpromptUpper[iPt].append(TF1(f'fNfdNpromptUpper{iPt}{iCutSet+1}',
                                                 '[1]*x + [0]', 0., max(corrYields)/2.))
                fNfdNpromptLower[iPt].append(TF1(f'fNfdNpromptLower{iPt}{iCutSet+1}',
                                                 '[1]*x + [0]', 0., max(corrYields)/2.))
                fNfdNpromptUpper[iPt][iCutSet].SetTitle(f'Lower Limit cutset{iCutSet+1}')
                fNfdNpromptLower[iPt][iCutSet].SetTitle(f'Upper Limit cutset{iCutSet+1}')
                fNfdNpromptUpper[iPt][iCutSet].SetParameter(0, (rawY+rawYunc)/(effP+effPunc))
                fNfdNpromptUpper[iPt][iCutSet].SetParameter(1, -(effF+effFunc)/(effP+effPunc))
                fNfdNpromptLower[iPt][iCutSet].SetParameter(0, (rawY-rawYunc)/(effP-effPunc))
                fNfdNpromptLower[iPt][iCutSet].SetParameter(1, -(effF-effFunc)/(effP-effPunc))
            fNfdNprompt[iPt][iCutSet].GetYaxis().SetTitle('#it{N}_{prompt}')
            fNfdNprompt[iPt][iCutSet].GetXaxis().SetTitle('#it{N}_{feed-down}')
            fNfdNprompt[iPt][iCutSet].GetYaxis().SetRangeUser(0., 1.5*max(corrYields))
            fNfdNprompt[iPt][iCutSet].SetTitle('')
            fNfdNprompt[iPt][iCutSet].SetLineColor(kRainBow+2*iCutSet)
            cLinearPlot[iPt].cd()
            if iCutSet != 0:
                fNfdNprompt[iPt][iCutSet].Draw('same')
                legendLinearPlot[iPt].AddEntry(fNfdNprompt[iPt][iCutSet], f'cutset{iCutSet+1}', 'l')
            else:
                fNfdNprompt[iPt][iCutSet].Draw()
                legendLinearPlot[iPt].AddEntry(fNfdNprompt[iPt][iCutSet], f'cutset{iCutSet+1}', 'l')
            if cutSetCfg['linearplot']['uncbands']:
                fNfdNpromptUpper[iPt][iCutSet].SetLineColor(kRainBow+2*iCutSet)
                fNfdNpromptLower[iPt][iCutSet].SetLineColor(kRainBow+2*iCutSet)
                fNfdNpromptUpper[iPt][iCutSet].SetLineStyle(7)
                fNfdNpromptLower[iPt][iCutSet].SetLineStyle(7)
                fNfdNpromptUpper[iPt][iCutSet].Draw('same')
                legendLinearPlot[iPt].AddEntry(fNfdNpromptUpper[iPt][iCutSet], f'lowerlimit cutset{iCutSet+1}')
                fNfdNpromptLower[iPt][iCutSet].Draw('same')
                legendLinearPlot[iPt].AddEntry(fNfdNpromptUpper[iPt][iCutSet], f'upperlimit cutset{iCutSet+1}')
            legendLinearPlot[iPt].Draw()
            cLinearPlot[iPt].Update()

        # prompt fraction
        fPrompt = effP * corrYields.item(0) / (effP * corrYields.item(0) + effF * corrYields.item(1))
        defPdeNP = (effP * (effP * corrYields.item(0) + effF * corrYields.item(1)) - effP**2
                    * corrYields.item(0)) / (effP * corrYields.item(0) + effF * corrYields.item(1))**2
        defPdeNF = - effF * effP * corrYields.item(0) / (effP * corrYields.item(0) + effF * corrYields.item(1))**2
        fPromptUnc = np.sqrt(defPdeNP**2 * covMatrixCorrYields.item(0, 0) +
                             defPdeNF**2 * covMatrixCorrYields.item(1, 1) +
                             2 * defPdeNP * defPdeNF * covMatrixCorrYields.item(1, 0))

        # feed-down fraction
        fFD = effF * corrYields.item(1) / (effP * corrYields.item(0) + effF * corrYields.item(1))
        defFdeNF = (effF * (effF * corrYields.item(1) + effP * corrYields.item(0)) - effF**2
                    * corrYields.item(1)) / (effP * corrYields.item(0) + effF * corrYields.item(1))**2
        defFdeNP = - effF * effP * corrYields.item(1) / (effP * corrYields.item(0) + effF * corrYields.item(1))**2
        fFDUnc = np.sqrt(defFdeNF**2 * covMatrixCorrYields.item(1, 1) +
                         defFdeNP**2 * covMatrixCorrYields.item(0, 0) +
                         2 * defFdeNF * defFdeNP * covMatrixCorrYields.item(1, 0))

        hPromptFracVsCut[iPt].SetBinContent(iCutSet+1, fPrompt)
        hPromptFracVsCut[iPt].SetBinError(iCutSet+1, fPromptUnc)
        hFDFracVsCut[iPt].SetBinContent(iCutSet+1, fFD)
        hFDFracVsCut[iPt].SetBinError(iCutSet+1, fFDUnc)

        # theory-driven, if enabled
        ptCent = (ptMax + ptMin) / 2.
        if isinstance(RaaPrompt_config, str):
            if ptMinRaaPrompt < ptCent < ptMaxRaaPrompt:
                RaaPrompt = RaaPromptSpline['yCent'](ptCent)
            elif ptCent > ptMaxRaaPrompt:
                RaaPrompt = RaaPromptSpline['yCent'](ptMaxRaaPrompt)
            else:
                RaaPrompt = RaaPromptSpline['yCent'](ptMinRaaPrompt)
            RaaPrompt = float(RaaPrompt)
        if isinstance(RaaFD_config, str):
            if ptMinRaaFD < ptCent < ptMaxRaaFD:
                RaaFD = RaaFDSpline['yCent'](ptCent)
            elif ptCent > ptMaxRaaFD:
                RaaFD = RaaFDSpline['yCent'](ptMaxRaaFD)
            else:
                RaaFD = RaaFDSpline['yCent'](ptMinRaaFD)
            RaaFD = float(RaaFD)
        if compareToFc:
            fPromptFc, fFDFc = GetPromptFDFractionFc(effP, effF, crossSecPrompt, crossSecFD, RaaPrompt, RaaFD)
            gPromptFracFcVsCut[iPt].SetPoint(iCutSet, iCutSet+1, fPromptFc[0])
            gPromptFracFcVsCut[iPt].SetPointError(iCutSet, 0.5, 0.5, fPromptFc[0] - fPromptFc[1],
                                                  fPromptFc[2] - fPromptFc[0])
            gFDFracFcVsCut[iPt].SetPoint(iCutSet, iCutSet+1, fFDFc[0])
            gFDFracFcVsCut[iPt].SetPointError(iCutSet, 0.5, 0.5, fFDFc[0] - fFDFc[1], fFDFc[2] - fFDFc[0])

        if compareToNb:
            fPromptNb = GetFractionNb(rawY, effP, effF, crossSecFD, ptMax-ptMin, 1., 1.,
                                      hEv[iCutSet].GetBinContent(1), sigmaMB)
            fFDNb = [1 - fPromptNb[0], 1 - fPromptNb[2], 1 - fPromptNb[1]] #inverse Nb method not reliable
            gPromptFracNbVsCut[iPt].SetPoint(iCutSet, iCutSet+1, fPromptNb[0])
            gPromptFracNbVsCut[iPt].SetPointError(iCutSet, 0.5, 0.5, fPromptNb[0] - fPromptNb[1],
                                                  fPromptNb[2] - fPromptNb[0])
            gFDFracNbVsCut[iPt].SetPoint(iCutSet, iCutSet+1, fFDNb[0])
            gFDFracNbVsCut[iPt].SetPointError(iCutSet, 0.5, 0.5, fFDNb[0] - fFDNb[1], fFDNb[2] - fFDNb[0])

    if iPt == 0:
        legDistr.AddEntry(hRawYieldsVsCut[iPt], 'Measured raw yield', 'lpe')
        legDistr.AddEntry(hRawYieldPromptVsCut[iPt], 'Prompt', 'f')
        legDistr.AddEntry(hRawYieldFDVsCut[iPt], 'Non-prompt', 'f')
        legDistr.AddEntry(hRawYieldsVsCutReSum[iPt], 'Prompt + non-prompt', 'l')
        legEff.AddEntry(hEffPromptVsCut[iPt], 'Prompt', 'lpe')
        legEff.AddEntry(hEffFDVsCut[iPt], 'Non-prompt', 'lpe')
        legFrac.AddEntry(hPromptFracVsCut[iPt], 'Prompt', 'lpe')
        legFrac.AddEntry(hFDFracVsCut[iPt], 'Non-prompt', 'lpe')

        deltaY = 0.
        if compareToFc:
            legFrac.AddEntry(gPromptFracFcVsCut[iPt], 'Prompt #it{f}_{c}', 'fp')
            legFrac.AddEntry(gFDFracFcVsCut[iPt], 'Non-prompt #it{f}_{c}', 'fp')
            deltaY += 0.1
            legFrac.SetY1(0.83 - deltaY)
        if compareToNb:
            legFrac.AddEntry(gPromptFracNbVsCut[iPt], 'Prompt #it{N}_{b}', 'fp')
            legFrac.AddEntry(gFDFracNbVsCut[iPt], 'Non-prompt #it{N}_{b}', 'fp')
            deltaY += 0.1
            legFrac.SetY1(0.83 - deltaY)

    cEff.append(TCanvas(f'cEff_{ptString}', '', 800, 800))
    cEff[iPt].DrawFrame(0.5, hEffPromptVsCut[iPt].GetMinimum()/5, nSets + 0.5, 1., f'{commonString};efficiency')
    cEff[iPt].SetLogy()
    hEffPromptVsCut[iPt].DrawCopy('same')
    hEffFDVsCut[iPt].DrawCopy('same')
    legEff.Draw()

    cDistr.append(TCanvas(f'cDistr_{ptString}', '', 800, 800))
    hFrameDistr = cDistr[iPt].DrawFrame(0.5, 0., nSets + 0.5, hRawYieldsVsCut[iPt].GetMaximum() * 1.2,
                                        f'{commonString};raw yield')
    hFrameDistr.GetYaxis().SetDecimals()
    hRawYieldsVsCut[iPt].Draw('same')
    hRawYieldPromptVsCut[iPt].DrawCopy('histsame')
    hRawYieldFDVsCut[iPt].DrawCopy('histsame')
    hRawYieldsVsCutReSum[iPt].Draw('same')
    legDistr.Draw()
    latInfo.DrawLatex(0.47, 0.65, f'#chi^{{2}} / ndf = {chiSquare:.3f}')

    cFrac.append(TCanvas(f'cFrac_{ptString}', '', 800, 800))
    cFrac[iPt].DrawFrame(0.5, 0., nSets + 0.5, 1.8, f'{commonString};fraction')
    hPromptFracVsCut[iPt].DrawCopy('Esame')
    hFDFracVsCut[iPt].DrawCopy('Esame')
    if compareToFc:
        gPromptFracFcVsCut[iPt].Draw('2PZ')
        gFDFracFcVsCut[iPt].Draw('2PZ')
    if compareToNb:
        gPromptFracNbVsCut[iPt].Draw('2PZ')
        gFDFracNbVsCut[iPt].Draw('2PZ')
    legFrac.Draw()

    cCorrMatrix.append(TCanvas(f'cCorrMatrix_{ptString}', '', 800, 800))
    cCorrMatrix[-1].cd().SetRightMargin(0.14)
    hCorrMatrixCutSets[iPt].Draw('colz')

nPtBins = hCorrYieldPrompt.GetNbinsX()
cCorrYield = TCanvas('cCorrYield', '', 800, 800)
cCorrYield.DrawFrame(hCorrYieldPrompt.GetBinLowEdge(1), 1.,
                     hCorrYieldPrompt.GetBinLowEdge(nPtBins) + hCorrYieldPrompt.GetBinWidth(nPtBins),
                     hCorrYieldPrompt.GetMaximum() * 1.2, ';#it{p}_{T} (GeV/#it{c});corrected yield')
cCorrYield.SetLogy()
hCorrYieldPrompt.Draw('same')
hCorrYieldFD.Draw('same')
legEff.Draw()

outFile = TFile(args.outFileName, 'recreate')
cCorrYield.Write()
hCorrYieldPrompt.Write()
hCorrYieldFD.Write()
for covElem in product(range(2), range(2)):
    hCovCorrYields[covElem[0]][covElem[1]].Write()
for iPt in range(hRawYields[0].GetNbinsX()):
    cDistr[iPt].Write()
    cEff[iPt].Write()
    cFrac[iPt].Write()
    hRawYieldsVsCut[iPt].Write()
    hRawYieldPromptVsCut[iPt].Write()
    hRawYieldFDVsCut[iPt].Write()
    hRawYieldsVsCutReSum[iPt].Write()
    hEffPromptVsCut[iPt].Write()
    hEffFDVsCut[iPt].Write()
    hPromptFracVsCut[iPt].Write()
    hFDFracVsCut[iPt].Write()
    hCorrMatrixCutSets[iPt].Write()
    if cutSetCfg['linearplot']['enable']:
        cLinearPlot[iPt].Write()
outFile.Close()

for iPt in range(hRawYields[0].GetNbinsX()):
    if iPt == 0:
        cEff[iPt].SaveAs(f'{outFileNameEffPDF}[')
        cDistr[iPt].SaveAs(f'{outFileNameDistrPDF}[')
        cFrac[iPt].SaveAs(f'{outFileNameFracPDF}[')
        cCorrMatrix[iPt].SaveAs(f'{outFileNameCorrMatrixPDF}[')
    cEff[iPt].SaveAs(outFileNameEffPDF)
    cDistr[iPt].SaveAs(outFileNameDistrPDF)
    cFrac[iPt].SaveAs(outFileNameFracPDF)
    cCorrMatrix[iPt].SaveAs(outFileNameCorrMatrixPDF)
    if iPt == hRawYields[0].GetNbinsX() - 1:
        cEff[iPt].SaveAs(f'{outFileNameEffPDF}]')
        cDistr[iPt].SaveAs(f'{outFileNameDistrPDF}]')
        cFrac[iPt].SaveAs(f'{outFileNameFracPDF}]')
        cCorrMatrix[iPt].SaveAs(f'{outFileNameCorrMatrixPDF}]')
    if cutSetCfg['linearplot']['enable']:
        for iformat in cutSetCfg['linearplot']['outfileformat']:
            outFileNameLinPlot = args.outFileName.replace('.root', f'_LinearPlot{iPt+1}_{iPt+2}.{iformat}')
            cLinearPlot[iPt].SaveAs(f'{outFileNameLinPlot}')
input('Press enter to exit')
