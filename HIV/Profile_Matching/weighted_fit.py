import numpy as np
import pylab
from scipy.optimize import curve_fit
from math import log10
from math import exp


# add calculation of fit

# object to hold a fit result
from file_parse import get_all_profiles


class FitResult:
    def __init__(self, slope, y_intercept, r):
        self.y_intercept = y_intercept
        self.slope = slope
        self.r = r

    # calculate year based on percent
    def calcYear(self, percent, default_year):
        try:
            return (percent - self.y_intercept) / self.slope
        except ZeroDivisionError:
            if percent == self.y_intercept:
                return default_year
            else:
                return float('inf')


# calculate r square value of a linear regression, referencing following site
# https://en.wikipedia.org/wiki/Coefficient_of_determination#Definitions
def calc_r_squared(slope, y_intercept, x_data, y_data):

    if len(x_data) != len(y_data):
        raise Exception("input data size mis-match")

    def average(arr):
        total = 0
        for i in arr:
            total += i
        return total / len(arr)

    def sum_squares(arr):
        avg = average(arr)
        var = 0
        for i in arr:
            var += (i - avg) ** 2
        return var

    def sum_residual(slope, y_intercept, x_data, y_data):
        total = 0
        for x, y in zip(x_data, y_data):
            f_i = x * slope + y_intercept
            total += (y - f_i) ** 2
        return total

    sum_squares_tot = sum_squares(y_data)
    sum_squares_residual = sum_residual(slope, y_intercept, x_data, y_data)
    return 1 - sum_squares_residual / sum_squares_tot


# take a profile and compute its weighted linear fit
def calcFit(profile):

    def checkEqual(arr):
        for i in range(0, len(arr) - 1):
            if arr[i] != arr[i + 1]:
                return False
        return True

    profile.remove_0_isolates()

    # to avoid float number round off errors, manually check if all data points are same
    # and assign slope = 0, y_intercept = any data point value, and r square = 1 (perfect fit)
    if checkEqual(profile.distr):
        params = [0, profile.distr[0]]
        r_squared = 1
    else:
        # calculate fit parameters
        sigmas = np.array([1 / n ** .5 for n in profile.numIso]) # weights
        params, cov = curve_fit(lambda x, a, b: a * x + b, profile.years,
                                profile.distr, sigma=sigmas, absolute_sigma=False)
        r_squared = calc_r_squared(params[0], params[1], profile.years, profile.distr)
    profile.fit = FitResult(params[0], params[1], r_squared)


# calculate euclidean distance, Prof. Haim's approach, p1 and p2 are profiles
def euclideanDist(p1, p2):

    L = 100
    k = -1.2
    x_0 = 5
    logiFunc = lambda x: L / (1 + exp(k * (x - x_0)))  # logistic function
    logConvert = lambda x: 0 if x == 0 else log10(x) + 1  # log convert
    combinedFunc = lambda x: logiFunc(logConvert(x))  # combined logistic and log

    # apply transform to data, then square them
    p1 = [combinedFunc(i) for i in p1.distr]
    p2 = [combinedFunc(i) for i in p2.distr]

    # compute euclidean distances
    eucDist = lambda x, y: sum([(a - b) ** 2 for a, b in zip(p1, p2)]) ** .5
    return eucDist(p1, p2)


def main():
    all_profiles = get_all_profiles()
    p = all_profiles.profiles[2]
    x = p.years
    yexact = p.distr
    y = []
    for i in x:
        y.append(p.fit.slope * i + p.fit.y_intercept)
    pylab.plot(x, yexact, 'o', label='Exact')
    pylab.plot(x, y, label='weighted fit')
    pylab.legend(loc='upper right')
    pylab.show()


# actual main
if __name__ == '__main__':
    main()
