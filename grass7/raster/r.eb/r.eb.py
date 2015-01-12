#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
#
# MODULE:       r.eb
# AUTHOR(S):    Paulo van Breugel <p.vanbreugel AT gmail.com>
# PURPOSE:      Compute the envirionmental bias (EB). If A is an areas within a
#               larger region B, the EB represents how much envirionmental
#               conditions in A deviate from median conditions in B. The first
#               step is to compute the multi-envirionmental similarity (MES)
#               for B, using all raster cells in B as reference points. The MES
#               of a raster cell thus represent how much conditions deviate
#               from median conditions in B. The EB is then computed as the
#               absolute difference of the median of MES values in A (MESa)
#               and median of MES values in B (MESb), divided by the median of
#               the absolute deviations of MESb from the median of MESb (MAD)
#
# COPYRIGHT: (C) 2015 Paulo van Breugel
#            http://ecodiv.org
#            http://pvanb.wordpress.com/
#
#            This program is free software under the GNU General Public
#            License (>=v2). Read the file COPYING that comes with GRASS
#            for details.
#
########################################################################
#
#%Module
#% description: Compute the environmental bias
#%End

#%option
#% key: env
#% type: string
#% gisprompt: old,cell,raster
#% description: Raster map(s) of environmental conditions
#% key_desc: names
#% required: yes
#% multiple: yes
#% guisection: Input
#%end

#%option
#% key: ref
#% type: string
#% gisprompt: old,cell,raster
#% description: Area for which EB should be computed (binary map with 1 and 0)
#% key_desc: names
#% required: yes
#% guisection: Input
#%end

#%option
#% key: output
#% type: string
#% gisprompt: new,cell,raster
#% description: Output MES layer (and root for IES layers if kept)
#% key_desc: names
#% required: no
#% multiple: no
#% guisection: Output
#%end

#%option
#% key: file
#% type: string
#% gisprompt: new
#% description: Name of output text file (csv format)
#% key_desc: name
#% required: no
#% guisection: Output
#%end

#%flag
#% key: i
#% description: Compute EB individual variables (IES)
#% guisection: Output
#%end

#%flag
#% key: m
#% description: Use minimum values of IES layers to compute MES (MES_min)
#% guisection: Output
#%end

#%flag
#% key: n
#% description: Use mean values of IES layers to compute MES (MES_av)
#% guisection: Output
#%end

#%flag
#% key: o
#% description: Use median values of IES layers to compute MES (MES_med)
#% guisection: Output
#%end

#%option
#% key: digits
#% type: integer
#% description: Precision of your input layers values
#% key_desc: string
#% answer: 5
#%end

#----------------------------------------------------------------------------
# Standard
#----------------------------------------------------------------------------

# import libraries
import os
import sys
import csv
import numpy as np
import uuid
import operator
import atexit
import tempfile
import string
import grass.script as grass

if not os.environ.has_key("GISBASE"):
    grass.message("You must be in GRASS GIS to run this program.")
    sys.exit(1)

# create set to store names of temporary maps to be deleted upon exit
clean_rast = set()

def cleanup():
    for rast in clean_rast:
        grass.run_command("g.remove", type="rast", name=rast, quiet=True)

#----------------------------------------------------------------------------
# Functions
#----------------------------------------------------------------------------

# Create temporary name
def tmpname(name):
    tmpf = name + "_" + str(uuid.uuid4())
    tmpf = string.replace(tmpf, '-', '_')
    clean_rast.add(tmpf)
    return tmpf

# Create temporary filename
def CreateFileName(outputfile):
    flname = outputfile
    k = 0
    while os.path.isfile(flname):
        k = k + 1
        fn = flname.split('.')
        if len(fn) == 1:
            flname = fn[0] + "_" + str(k)
        else:
            flname = fn[0] + "_" + str(k) + "." + fn[1]
    return flname

def CheckLayer(envlay):
    for chl in xrange(len(envlay)):
        ffile = grass.find_file(envlay[chl], element = 'cell')
        if ffile['fullname'] == '':
            grass.fatal("The layer " + envlay[chl] + " does not exist.")

# Write color rule file
def defcol(mapname):
    # Color table
    tmpcol = tempfile.mkstemp()
    text_file = open(tmpcol[1], "w")
    text_file.write("0% 244:109:67\n")
    text_file.write("50 255:255:210\n")
    text_file.write("100% 50:136:189\n")
    text_file.close()
    # Assign color table
    grass.run_command("r.colors", flags="n", quiet=True, map=mapname, rules=tmpcol[1])
    os.remove(tmpcol[1])

# Compute EB for input file (simlay = similarity, reflay = reference layer)
def EB(simlay, reflay):

    # layer name
    vn = simlay.split("@")[0]

    # Median and mad for whole region (within current mask)
    tmpf4 = tmpname('reb4')
    d = grass.read_command("r.quantile", quiet=True, input=simlay, percentiles="50")
    d = d.split(":")
    d = float(string.replace(d[2], "\n", ""))
    grass.mapcalc("$tmpf4 = abs($map - $d)",
                  map=simlay,
                  tmpf4=tmpf4,
                  d=d, quiet=True)
    mad = grass.read_command("r.quantile", quiet=True, input=tmpf4, percentiles="50")
    mad = mad.split(":")
    mad = float(string.replace(mad[2], "\n", ""))
    grass.run_command("g.remove", quiet=True, flags="f", type="raster", name=tmpf4)

    # Median and mad for reference layer
    tmpf5 = tmpname('reb5')
    clean_rast.add(tmpf5)
    grass.run_command("r.null", map=reflay, setnull=0)
    chlay = grass.parse_command("r.info", flags="r", map=reflay)
    if chlay['max'] != '1' or chlay['min'] != '1':
        grass.warning('please note that your layer is not a binary layer. Continuing assuming that all values other than 0 mark the area of interest')
        grass.mapcalc("$tmpf5 = if($reflay != 0, 1, null())",
                      tmpf5=tmpf5, reflay=reflay, quiet=True)
    else:
        grass.run_command("g.copy", raster=(reflay,tmpf5), quiet=True)
    grass.mapcalc("$tmpf5 = $tmpf5 * $simlay", tmpf5=tmpf5,
                  simlay=simlay, quiet=True, overwrite=True)
    e = grass.read_command("r.quantile", quiet=True, input=tmpf5, percentiles="50")
    e = e.split(":")
    e = float(string.replace(e[2], "\n", ""))
    EBstat = abs(d - e) / mad

    # Print results to screen and return results
    grass.info("Median " + vn + " (all region) = " + str(d))
    grass.info("Median " + vn + " (ref. area) = " + str(e))
    grass.info("MAD " + vn + " (all region) = " + str(mad))
    grass.info("EB = " + str(EBstat))

    # Clean up and return data
    grass.run_command("g.remove", flags="f", type="raster", name=tmpf5, quiet=True)
    return (mad, d, e, EBstat)


def main():

    #----------------------------------------------------------------------------
    # Variables
    #----------------------------------------------------------------------------

#Test
#options = {"env":"bio_1@climate,bio_2@climate,bio_3@climate", "file":"test.txt", "ref":"PAs2", "output":"AA1", "digits":"5"}
#flags = {"m":True, "n":True, "o":True, "i":True}

    # variables
    ipl = options['env']
    ipl = ipl.split(',')
    CheckLayer(ipl)
    ipn = [z.split('@')[0] for z in ipl]
    ipn = [x.lower() for x in ipn]
    out = options['output']
    if out == '':
        tmpf0 = tmpname('reb0')
    else:
        tmpf0 = out
    filename = options['file']
    if filename != '':
        filename = CreateFileName(filename)
    ref = options['ref']
    flag_m = flags['m']
    flag_n = flags['n']
    flag_o = flags['o']
    flag_i = flags['i']
    digits = int(options['digits'])
    digits2 = pow(10, digits)

    #----------------------------------------------------------------------------
    # Compute MES
    #----------------------------------------------------------------------------

    ipi = []
    for j in xrange(len(ipl)):

        # Calculate the frequency distribution
        tmpf1 = tmpname('reb1')
        grass.mapcalc("$tmpf1 = int($dignum * $inplay)",
                      tmpf1=tmpf1,
                      inplay=ipl[j],
                      dignum=digits2,
                      quiet=True)
        p = grass.pipe_command('r.stats', quiet=True, flags='cn', input=tmpf1, sort='asc', sep=';')
        stval = {}
        for line in p.stdout:
            [val, count] = line.strip(os.linesep).split(';')
            stval[float(val)] = float(count)
        p.wait()
        sstval = sorted(stval.items(), key=operator.itemgetter(0))
        sstval = np.matrix(sstval)
        a = np.cumsum(np.array(sstval), axis=0)
        b = np.sum(np.array(sstval), axis=0)
        c = a[:,1] / b[1] * 100

        # Create recode rules
        e1 = np.min(np.array(sstval), axis=0)[0] - 99999
        e2 = np.max(np.array(sstval), axis=0)[0] - 99999
        a1 = np.hstack([(e1), np.array(sstval.T[0])[0, :]])
        a2 = np.hstack([np.array(sstval.T[0])[0,:] -1, (e2)])
        b1 = np.hstack([(0), c])

        tmprule = tempfile.mkstemp()
        text_file = open(tmprule[1], "w")
        for k in np.arange(0, len(b1.T)):
            rtmp = str(int(a1[k])) + ":" + str(int(a2[k])) + ":" + str(b1[k])
            text_file.write(rtmp + "\n")
        text_file.close()

        # Create the recode layer and calculate the IES
        tmpf2 = tmpname('reb2')
        grass.run_command("r.recode", input=tmpf1, output=tmpf2, rules=tmprule[1])

        tmpf3 = tmpname('reb3')
        z1 = tmpf3 + " = if(" + tmpf2 + "<=50, 2*float(" + tmpf2 + ")"
        z3 = ", if(" + tmpf2 + "<100, 2*(100-float(" + tmpf2 + "))))"
        calcc = z1 + z3
        grass.mapcalc(calcc, quiet=True)
        grass.run_command("g.remove", quiet=True, flags="f", type="raster", name=tmpf2)
        grass.run_command("g.remove", quiet=True, flags="f", type="raster", name=tmpf1)
        #os.remove(tmprule[1])
        ipi.append(tmpf3)

    #-----------------------------------------------------------------------
    # Calculate EB statistics
    #-----------------------------------------------------------------------

    if flag_i or flag_m or flag_n or flag_o:

        # EB MES
        if flag_m:
            nmn = tmpf0 + "_MES_mean"
            grass.run_command("r.series", quiet=True, output=nmn, input=tuple(ipi), method="average")
            defcol(nmn)
            ebm = EB(simlay=nmn, reflay=ref)

        if flag_n:
            nmn = tmpf0 + "_MES_median"
            grass.run_command("r.series", quiet=True, output=nmn, input=tuple(ipi), method="median")
            defcol(nmn)
            ebn = EB(simlay=nmn, reflay=ref)

        if flag_o:
            nmn = tmpf0 + "_MES_minimum"
            grass.run_command("r.series", quiet=True, output=nmn, input=tuple(ipi), method="minimum")
            defcol(nmn)
            ebo = EB(simlay=nmn, reflay=ref)

        # EB individual layers
        if flag_i:
            ebi = {}
            for mm in xrange(len(ipi)):
                nmn = tmpf0 + "_" + ipn[mm]
                grass.run_command("g.rename", quiet=True, raster=(ipi[mm], nmn))
                defcol(nmn)
                value = EB(simlay=nmn, reflay=ref)
                ebi[nmn] = value
        else:
            grass.run_command("g.remove", quiet=True, flags="f", type="raster", name=ipi)
    else:
        grass.fatal("You need to select at least one of IES/MES_med/MES_av/MES_min options")

    if filename != '':
        with open(filename, 'wb') as csvfile:
            fieldnames = ['variable', 'median_region', 'median_reference', 'mad', 'eb']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            if flag_m:
                writer.writerow({'variable':'MES_mean', 'median_region':ebm[0],
                                'median_reference':ebm[1],'mad':ebm[2],'eb':ebm[3]})
            if flag_n:
                writer.writerow({'variable':'MES_mean','median_region':ebm[0],
                    'median_reference':ebm[1], 'mad':ebm[2],'eb':ebm[3]})
            if flag_n:
                writer.writerow({'variable':'MES_median', 'median_region':ebn[0],
                    'median_reference':ebn[1], 'mad':ebn[2],'eb':ebn[3]})
            if flag_o:
                writer.writerow({'variable':'MES_minimum','median_region':ebo[0],
                    'median_reference':ebo[1], 'mad':ebo[2],'eb':ebo[3]})
            if flag_i:
                mykeys = ebi.keys()
                for vari in mykeys:
                    ebj = ebi[vari]
                    writer.writerow({'variable':vari,'median_region':ebj[0],
                        'median_reference':ebj[1], 'mad':ebj[2],'eb':ebj[3]})
        grass.info("\nThe results are written to " + filename + "\n")
        grass.info("\n-------------------------------------------\n")

if __name__ == "__main__":
    options, flags = grass.parser()
    atexit.register(cleanup)
    sys.exit(main())

