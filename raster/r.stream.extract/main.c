
/****************************************************************************
 *
 * MODULE:       r.stream.extract
 * AUTHOR(S):    Markus Metz <markus.metz.giswork gmail.com>
 * PURPOSE:      Hydrological analysis
 *               Extracts stream networks from accumulation raster with
 *               given threshold
 * COPYRIGHT:    (C) 1999-2009 by the GRASS Development Team
 *
 *               This program is free software under the GNU General Public
 *               License (>=v2). Read the file COPYING that comes with GRASS
 *               for details.
 *
 *****************************************************************************/
#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <grass/gis.h>
#include <grass/glocale.h>
#include "local_proto.h"

char drain[3][3] = { {7, 6, 5}, {8, 0, 4}, {1, 2, 3} };


int main(int argc, char *argv[])
{
    struct
    {
	struct Option *ele, *acc, *weight;
	struct Option *threshold, *d8cut;
	struct Option *mont_exp;
    } input;
    struct
    {
	struct Option *stream_rast;
	struct Option *stream_vect;
	struct Option *dir_rast;
    } output;
    struct GModule *module;
    int ele_fd, acc_fd, weight_fd;
    double threshold, d8cut, mont_exp;
    char *mapset;

    G_gisinit(argv[0]);

    /* Set description */
    module = G_define_module();
    module->keywords = _("raster");
    module->description = _("Stream network extraction");

    input.ele = G_define_standard_option(G_OPT_R_INPUT);
    input.ele->key = "elevation";
    input.ele->label = _("Elevation map");
    input.ele->description = _("Elevation on which entire analysis is based");

    input.acc = G_define_standard_option(G_OPT_R_INPUT);
    input.acc->key = "accumulation";
    input.acc->label = _("Accumulation map");
    input.acc->required = NO;
    input.acc->description =
	_("Stream extraction will use provided accumulation instead of calculating it anew");

    input.weight = G_define_standard_option(G_OPT_R_INPUT);
    input.weight->key = "weight";
    input.weight->label = _("Weight map for accumulation");
    input.weight->required = NO;
    input.weight->description =
	_("Map used as weight for flow accumulation when initiating streams");

    input.threshold = G_define_option();
    input.threshold->key = "threshold";
    input.threshold->label = _("Minimum flow accumulation for streams");
    input.threshold->description = _("Must be > 0");
    input.threshold->required = YES;
    input.threshold->type = TYPE_DOUBLE;

    input.d8cut = G_define_option();
    input.d8cut->key = "d8cut";
    input.d8cut->label = _("Use SFD above this threshold");
    input.d8cut->description =
	_("If accumulation is larger than d8cut, SFD is used instead of MFD."
	  " Applies only if no accumulation map is given.");
    input.d8cut->required = NO;
    input.d8cut->answer = "infinity";
    input.d8cut->type = TYPE_DOUBLE;

    input.mont_exp = G_define_option();
    input.mont_exp->key = "mexp";
    input.mont_exp->type = TYPE_DOUBLE;
    input.mont_exp->required = NO;
    input.mont_exp->answer = "0";
    input.mont_exp->label =
	_("Montgomery exponent for slope, disabled with 0");
    input.mont_exp->description =
	_("Montgomery: accumulation is multiplied with pow(slope,mexp) and then compared with threshold.");

    output.stream_rast = G_define_standard_option(G_OPT_R_OUTPUT);
    output.stream_rast->key = "stream_rast";
    output.stream_rast->description =
	_("Output raster map with unique stream ids");
    output.stream_rast->required = NO;
    output.stream_rast->guisection = _("Output options");

    output.stream_vect = G_define_standard_option(G_OPT_V_OUTPUT);
    output.stream_vect->key = "stream_vect";
    output.stream_vect->description =
	_("Output vector with unique stream ids");
    output.stream_vect->required = NO;
    output.stream_vect->guisection = _("Output options");

    output.dir_rast = G_define_standard_option(G_OPT_R_OUTPUT);
    output.dir_rast->key = "direction";
    output.dir_rast->description =
	_("Output raster map with flow direction for streams");
    output.dir_rast->required = NO;
    output.dir_rast->guisection = _("Output options");

    if (G_parser(argc, argv))
	exit(EXIT_FAILURE);

    /***********************/
    /*    check options    */

    /***********************/

    /* input maps exist ? */
    if (!G_find_cell(input.ele->answer, ""))
	G_fatal_error(_("Raster map <%s> not found"), input.ele->answer);

    if (input.acc->answer) {
	if (!G_find_cell(input.acc->answer, ""))
	    G_fatal_error(_("Raster map <%s> not found"), input.acc->answer);
    }

    if (input.weight->answer) {
	if (!G_find_cell(input.weight->answer, ""))
	    G_fatal_error(_("Raster map <%s> not found"),
			  input.weight->answer);
    }

    /* threshold makes sense */
    threshold = atof(input.threshold->answer);
    if (threshold <= 0)
	G_fatal_error(_("Threshold must be > 0 but is %f"), threshold);

    /* d8cut */
    if (strcmp(input.d8cut->answer, "infinity") == 0) {
	d8cut = DBL_MAX;
    }
    else {
	d8cut = atof(input.d8cut->answer);
	if (d8cut < 0)
	    G_fatal_error(_("d8cut must be positive or zero but is %f"),
			  d8cut);
    }

    /* Montgomery stream initiation */
    if (input.mont_exp->answer) {
	mont_exp = atof(input.mont_exp->answer);
	if (mont_exp < 0)
	    G_fatal_error(_("Montgomery exponent must be positive or zero but is %f"),
			  mont_exp);
	if (mont_exp > 3)
	    G_warning(_("Montgomery exponent is %f, recommended range is 0.0 - 3.0"),
		      mont_exp);
    }
    else
	mont_exp = 0;

    /* Check for some output map */
    if ((output.stream_rast->answer == NULL)
	&& (output.stream_vect->answer == NULL)) {
	G_fatal_error(_("Sorry, you must choose at least one output map."));
    }

    /*********************/
    /*    preparation    */

    /*********************/

    /* open input maps */
    mapset = G_find_cell2(input.ele->answer, "");
    ele_fd = G_open_cell_old(input.ele->answer, mapset);
    if (ele_fd < 0)
	G_fatal_error(_("could not open input map %s"), input.ele->answer);

    if (input.acc->answer) {
	mapset = G_find_cell2(input.acc->answer, "");
	acc_fd = G_open_cell_old(input.acc->answer, mapset);
	if (acc_fd < 0)
	    G_fatal_error(_("could not open input map %s"),
			  input.acc->answer);
    }
    else
	acc_fd = -1;

    if (input.weight->answer) {
	mapset = G_find_cell2(input.weight->answer, "");
	weight_fd = G_open_cell_old(input.weight->answer, mapset);
	if (weight_fd < 0)
	    G_fatal_error(_("could not open input map %s"),
			  input.weight->answer);
    }
    else
	weight_fd = -1;

    /* set global variables */
    nrows = G_window_rows();
    ncols = G_window_cols();
    sides = 8;			/* not a user option */
    c_fac = 5;			/* not a user option, MFD covergence factor 5 gives best results  */

    /* allocate memory */
    ele = (CELL *) G_malloc(nrows * ncols * sizeof(CELL));
    acc = (DCELL *) G_malloc(nrows * ncols * sizeof(DCELL));
    stream = (CELL *) G_malloc(nrows * ncols * sizeof(CELL));
    if (input.weight->answer)
	accweight = (DCELL *) G_malloc(nrows * ncols * sizeof(DCELL));
    else
	accweight = NULL;

    /* load maps */
    if (load_maps(ele_fd, acc_fd, weight_fd) < 0)
	G_fatal_error(_("could not load input map(s)"));

    /********************/
    /*    processing    */

    /********************/

    /* sort elevation and get initial stream direction */
    if (do_astar() < 0)
	G_fatal_error(_("could not sort elevation map"));

    /* extract streams */
    if (acc_fd < 0) {
	if (do_accum(d8cut) < 0)
	    G_fatal_error(_("could not calculate flow accumulation"));
	if (extract_streams
	    (threshold, mont_exp, (input.weight->answer != NULL)) < 0)
	    G_fatal_error(_("could not extract streams"));
    }
    else {
	if (extract_streams
	    (threshold, mont_exp, (input.weight->answer != NULL)) < 0)
	    G_fatal_error(_("could not extract streams"));
    }

    G_free(ele);
    G_free(acc);
    if (input.weight->answer)
	G_free(accweight);

    /* thin streams */
    if (thin_streams() < 0)
	G_fatal_error(_("could not extract streams"));

    /* write output maps */
    if (close_maps(output.stream_rast->answer, output.stream_vect->answer,
		   output.dir_rast->answer) < 0)
	G_fatal_error(_("could not write output maps"));

    G_free(stream);

    exit(EXIT_SUCCESS);
}
