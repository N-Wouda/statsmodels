# -*- coding: utf-8 -*-
"""Base classes for statistical test results

Created on Mon Apr 22 14:03:21 2013

Author: Josef Perktold
"""
import numpy as np

from statsmodels.compat.python import lzip, zip
from statsmodels.tools.decorators import nottest


class AllPairsResults(object):
    '''Results class for pairwise comparisons, based on p-values

    Parameters
    ----------
    pvals_raw : array_like, 1-D
        p-values from a pairwise comparison test
    all_pairs : list of tuples
        list of indices, one pair for each comparison
    multitest_method : string
        method that is used by default for p-value correction. This is used
        as default by the methods like if the multiple-testing method is not
        specified as argument.
    levels : None or list of strings
        optional names of the levels or groups
    n_levels : None or int
        If None, then the number of levels or groups is inferred from the
        other arguments. It can be explicitly specified, if the inferred
        number is incorrect.

    Notes
    -----
    This class can also be used for other pairwise comparisons, for example
    comparing several treatments to a control (as in Dunnet's test).

    '''


    def __init__(self, pvals_raw, all_pairs, multitest_method='hs',
                 levels=None, n_levels=None):
        self.pvals_raw = pvals_raw
        self.all_pairs = all_pairs
        if n_levels is None:
            # for all_pairs nobs*(nobs-1)/2
            #self.n_levels = (1. + np.sqrt(1 + 8 * len(all_pairs))) * 0.5
            self.n_levels = np.max(all_pairs) + 1
        else:
            self.n_levels = n_levels

        self.multitest_method = multitest_method
        self.levels = levels
        if levels is None:
            self.all_pairs_names = ['%r' % (pairs,) for pairs in all_pairs]
        else:
            self.all_pairs_names = ['%s-%s' % (levels[pairs[0]],
                                               levels[pairs[1]])
                                               for pairs in all_pairs]

    def pval_corrected(self, method=None):
        '''p-values corrected for multiple testing problem

        This uses the default p-value correction of the instance stored in
        ``self.multitest_method`` if method is None.

        '''
        import statsmodels.stats.multitest as smt
        if method is None:
            method = self.multitest_method
        #TODO: breaks with method=None
        return smt.multipletests(self.pvals_raw, method=method)[1]

    def __str__(self):
        return self.summary()

    def pval_table(self):
        '''create a (n_levels, n_levels) array with corrected p_values

        this needs to improve, similar to R pairwise output
        '''
        k = self.n_levels
        pvals_mat = np.zeros((k, k))
        # if we don't assume we have all pairs
        pvals_mat[lzip(*self.all_pairs)] = self.pval_corrected()
        #pvals_mat[np.triu_indices(k, 1)] = self.pval_corrected()
        return pvals_mat

    def summary(self):
        '''returns text summarizing the results

        uses the default pvalue correction of the instance stored in
        ``self.multitest_method``
        '''
        import statsmodels.stats.multitest as smt
        maxlevel = max((len(ss) for ss in self.all_pairs_names))

        text = 'Corrected p-values using %s p-value correction\n\n' % \
                        smt.multitest_methods_names[self.multitest_method]
        text += 'Pairs' + (' ' * (maxlevel - 5 + 1)) + 'p-values\n'
        text += '\n'.join(('%s  %6.4g' % (pairs, pv) for (pairs, pv) in
                zip(self.all_pairs_names, self.pval_corrected())))
        return text


class Hypothesis(object):

    def __init__(self, null, alternative):
        self._null = null
        self._alternative = alternative

    @property
    def null(self):
        return self._null

    @property
    def alternative(self):
        return self._alternative

    def __str__(self):
        return ("Hypotheses:\n\t* H0: {0}\n\t* H1: {1}"
                .format(self._null, self._alternative))


class CriticalValues(object):

    def __init__(self, crit_dict):
        self._crit_dict = crit_dict

    @property
    def crit_dict(self):
        return self._crit_dict

    def __str__(self):
        items = sorted(self._crit_dict.items(),
                       key=lambda item: int(item[0].strip("%")))

        critical_values = map(lambda item: "[{0}] = {1}".format(*item),
                              items)

        return "Critical values:\n" + ", ".join(critical_values)


class Statistics(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.print_filter = None

    @property
    def attributes(self):  # print_filter is internal
        return [key for key in self.__dict__.keys()
                if key != "print_filter"]

    def __str__(self):
        def _filter(key):
            return not self.print_filter or key in self.print_filter

        items = map(lambda item: "{0} = {1}".format(item, getattr(self, item)),
                    filter(_filter, self.attributes))

        return "Statistics:\n" + ", ".join(items)


@nottest
class TestResult(object):

    _options = ["test_name", "hypothesis", "statistics", "critical_values"]

    _warn = """
    While previously test results returned fields as class attributes, this 
    behaviour has changed. Statistics can now be accessed through the statistics
    attribute; other attributes may also be available, dependent on the type of
    test. You may use `test.attributes` and `test.statistics.attributes` to 
    discover all available attributes."
    """

    def __init__(self, test_name, statistics, print_filter=None, **kwargs):
        self.test_name = test_name

        self.statistics = statistics
        self.statistics.print_filter = print_filter

        for key, value in kwargs.items():
            if key in TestResult._options:
                setattr(self, key, value)

    @property
    def attributes(self):
        return [option for option in self._options
                if hasattr(self, option)]

    def __getattr__(self, item):
        import warnings

        if not hasattr(self.statistics, item):
            raise AttributeError("`{0}` is not an understood field on this "
                                 "TestResult.".format(item))

        warnings.warn(self._warn, DeprecationWarning)

        return getattr(self.statistics, item)

    def summary(self):
        values = [str(getattr(self, key))
                  for key in TestResult._options
                  if hasattr(self, key)]

        return "\n\n".join(values)

    def __str__(self):
        return self.summary()
