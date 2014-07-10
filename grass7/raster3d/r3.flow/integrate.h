#ifndef INTEGRATE_H
#define INTEGRATE_H

#include <grass/raster3d.h>

static const double MAX_ERROR = 1.0e-6;
static const double MIN_STEP = 0.01;
static const double MAX_STEP = 1;

/* Cash-Karp parameters */
static const double B[5][5] = { {1. / 5, 0, 0, 0, 0},
{3. / 40, 9. / 40, 0, 0, 0},
{3. / 10, -9. / 10, 6. / 5, 0, 0},
{-11. / 54, 5. / 2, -70. / 27, 35. / 27, 0},
{1631. / 55296, 175. / 512, 575. / 13824,
 44275. / 110592, 253. / 4096}
};
static const double C[6] =
    { 37. / 378, 0, 250. / 621, 125. / 594, 0, 512. / 1771 };
static const double DC[6] = { 37. / 378 - 2825. / 27648, 0,
    250. / 621 - 18575. / 48384, 125. / 594 - 13525. / 55296,
    -277. / 14336, 512. / 1771 - 1. / 4
};

double norm(const double x, const double y, const double z);
int get_velocity(RASTER3D_Region * region, RASTER3D_Map ** velocity_field,
		 const double x, const double y, const double z,
		 double *vel_x, double *vel_y, double *vel_z);
double get_time_step(const char *unit, const double step,
		     const double velocity, const double cell_size);
int rk45_integrate_next(RASTER3D_Region * region,
			RASTER3D_Map ** velocity_field, const double *point,
			double *next_point, double *delta_t,
			const double min_step, const double max_step);

#endif // INTEGRATE_H
