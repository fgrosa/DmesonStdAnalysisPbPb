"""
Utility script to compare the FONLL predictions for B and D from B
"""
import sys
import pandas as pd
import numpy as np
from root_numpy import fill_hist
from ROOT import TCanvas, TLegend, TH1D, gPad #pylint: disable=import-error,no-name-in-module
from ROOT import kRed, kAzure, kFullCircle, kFullSquare #pylint: disable=import-error,no-name-in-module
sys.path.insert(0, '..')
from utils.StyleFormatter import SetGlobalStyle, SetObjectStyle

def main():
    """
    main function of script
    """
    SetGlobalStyle(padleftmargin=0.18, padbottommargin=0.14, titleoffsety=1.6, maxdigits=2, optstat=0)

    n_bins = 1001
    bin_width = 0.05 # GeV
    bin_lims = [i * bin_width for i in range(0, n_bins + 1)]
    hFONLLBtoDCentral = TH1D('hDfromBpred_central',
                             ';#it{p}_{T} (GeV/#it{c});#frac{d#sigma}{d#it{p}_{T}} (pb GeV^{-1} #it{c})',
                             n_bins, np.asarray(bin_lims, 'd'))
    hFONLLBtoDMin = TH1D('hDfromBpred_min',
                         ';#it{p}_{T} (GeV/#it{c});#frac{d#sigma}{d#it{p}_{T}} (pb GeV^{-1} #it{c})',
                         n_bins, np.asarray(bin_lims, 'd'))
    hFONLLBtoDMax = TH1D('hDfromBpred_max',
                         ';#it{p}_{T} (GeV/#it{c});#frac{d#sigma}{d#it{p}_{T}} (pb GeV^{-1} #it{c})',
                         n_bins, np.asarray(bin_lims, 'd'))
    hFONLLBCentral = TH1D('hBpred_central',
                          ';#it{p}_{T} (GeV/#it{c});#frac{d#sigma}{d#it{p}_{T}} (pb GeV^{-1} #it{c})',
                          n_bins, np.asarray(bin_lims, 'd'))
    hFONLLBMin = TH1D('hBpred_min', ';#it{p}_{T} (GeV/#it{c});#frac{d#sigma}{d#it{p}_{T}} (pb GeV^{-1} #it{c})',
                      n_bins, np.asarray(bin_lims, 'd'))
    hFONLLBMax = TH1D('hBpred_max', ';#it{p}_{T} (GeV/#it{c});#frac{d#sigma}{d#it{p}_{T}} (pb GeV^{-1} #it{c})',
                      n_bins, np.asarray(bin_lims, 'd'))

    fonllBtoD_df = pd.read_csv("fonll/FONLL_DfromB_pp5_y05_toCook.txt", sep=" ", header=14).astype('float64')
    fonllB_df = pd.read_csv("fonll/FONLL_B_pp5_y05.txt", sep=" ", header=13).astype('float64')

    fill_hist(hFONLLBtoDCentral, fonllBtoD_df['pt'].values, fonllBtoD_df['central'].values)
    fill_hist(hFONLLBtoDMin, fonllBtoD_df['pt'].values, fonllBtoD_df['min'].values)
    fill_hist(hFONLLBtoDMax, fonllBtoD_df['pt'].values, fonllBtoD_df['max'].values)
    fill_hist(hFONLLBCentral, fonllB_df['pt'].values, fonllB_df['central'].values)
    fill_hist(hFONLLBMin, fonllB_df['pt'].values, fonllB_df['min'].values)
    fill_hist(hFONLLBMax, fonllB_df['pt'].values, fonllB_df['max'].values)

    for iBin in range(hFONLLBtoDCentral.GetNbinsX()):
        hFONLLBtoDCentral.SetBinError(iBin + 1, 1.e-3)
        hFONLLBtoDMin.SetBinError(iBin + 1, 1.e-3)
        hFONLLBtoDMax.SetBinError(iBin + 1, 1.e-3)
        hFONLLBCentral.SetBinError(iBin + 1, 1.e-3)
        hFONLLBMin.SetBinError(iBin + 1, 1.e-3)
        hFONLLBMax.SetBinError(iBin + 1, 1.e-3)


    hFONLL = [hFONLLBtoDCentral, hFONLLBtoDMin, hFONLLBtoDMax]
    hBFONLL = [hFONLLBCentral, hFONLLBMin, hFONLLBMax]
    labels = ['Central', 'Min', 'Max']
    canvas = []

    for label in labels:
        canvas.append(TCanvas(f'cComp{label}', '', 2000, 1000))

    for (histo, histo_std, label, canv) in zip(hFONLL, hBFONLL, labels, canvas):
        pt_lims = np.array(histo.GetXaxis().GetXbins(), 'd')

        pt_min = list(pt_lims)[0]
        pt_max = list(pt_lims)[-1]
        histo_std = histo_std.Rebin(histo.GetNbinsX(), f'hBFONLL{label}', pt_lims)
        histo.Rebin(5)
        histo_std.Rebin(5)
        histo.Scale(1.e-6)
        histo_std.Scale(1.e-6)
        histo_ratio = histo.Clone(f'hRatioDfromBOverB{label}')
        histo_ratio.Divide(histo, histo_std)
        histo_ratio.GetYaxis().SetTitle('FONLL D from B / FONLL B')

        print(f'\nFONLL B {label} integral (ub): {histo_std.Integral("width"):.4e}')
        print(f'FONLL B from D {label} integral (ub): {histo.Integral("width"):.4e}\n')

        canv.Divide(2, 1)
        canv.cd(1).DrawFrame(pt_min, 1e-4, pt_max, 100.,
                             ';#it{p}_{T} (GeV/#it{c});#frac{d#sigma}{d#it{p}_{T}} (#mub GeV^{-1} #it{c})')
        leg = TLegend(0.4, 0.7, 0.8, 0.9)
        leg.SetTextSize(0.045)
        leg.SetBorderSize(0)
        leg.SetFillStyle(0)
        SetObjectStyle(histo, color=kAzure+4, markerstyle=kFullSquare)
        SetObjectStyle(histo_std, color=kRed, markerstyle=kFullCircle)
        histo.Draw('same')
        histo_std.Draw('same')
        leg.AddEntry(histo, f'FONLL D from B {label}', 'p')
        leg.AddEntry(histo_std, f'FONLL B {label}', 'p')
        gPad.SetLogy()
        leg.Draw()

        hframe_ratio = canv.cd(2).DrawFrame(pt_min, 0., pt_max, 3.5,
                                            ';#it{p}_{T} (GeV/#it{c}); FONLL D from B / FONLL B')
        hframe_ratio.GetYaxis().SetDecimals()
        SetObjectStyle(histo_ratio, color=kAzure+4, markerstyle=kFullSquare)
        histo_ratio.Draw('same')
        canv.Update()
        canv.SaveAs(f'CompFONLL_DfromBvsB_{label}.pdf')

    input('Press enter to exit')

main()
