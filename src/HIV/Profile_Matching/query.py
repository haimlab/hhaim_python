import sys
import csv
import constants
from file_parse import get_all_dynamic_profiles, calcYear
from weighted_fit import calcFit
from os.path import join


class QueryInput:
    def __init__(self, profile, position, year_range, clade, region):
        self.profile = profile
        self.position = position
        self.year_range = year_range
        self.clade = clade
        self.region = region


class Query:
    def __init__(self, query_input, all_profiles):
        self.all_profiles = all_profiles.filter(position=query_input.position)
        self.input = query_input
        self.results = {}  # {(clade, region) -> {amino acid -> year}}
        self.scores = {}  # {(clade, region) -> stdev of corresponding profile), for writing to file specifically
        self.best_match_years = {}  # {(clade, region) -> year)}
        self.fits = {}  # {(clade, region) -> {amino acid -> fit object}}
        self.best_fit_clade = None
        self.best_fit_region = None

        for aminoAcid in self.input.profile:
            sub_profiles = self.all_profiles.filter(aminoAcid=aminoAcid)
            for p in sub_profiles.get_all_profiles():
                if p.fit is None:
                    print(p.tag())
                self.add_result(p.clade(), p.region(), aminoAcid,
                                p.fit.calcYear(query_input.profile[aminoAcid],
                                calcYear(self.input.year_range)), p.fit)
        self.find_best_match()

    def add_result(self, clade, region, aminoAcid, year, fit):
        try:
            self.results[(clade, region)][aminoAcid] = year
            self.fits[(clade, region)][aminoAcid] = fit
        except KeyError:
            self.results[(clade, region)] = {aminoAcid: year}
            self.fits[(clade, region)] = {aminoAcid: fit}

    def find_best_match(self):

        def calc_avg_percentage(aa, clade, region):
            cand_prof = self.all_profiles.filter(clade=clade, region=region, aminoAcid=aa)
            if len(cand_prof.get_all_profiles()) != 1:
                for p in cand_prof.get_all_profiles():
                    print(p.position())
                print(len(cand_prof.get_all_profiles()))
                raise Exception('something went wrong')
            only_prof = cand_prof.get_all_profiles()[0]
            return sum(only_prof.distr) / len(only_prof.distr)

        def clac_r2_weighted_stdev(profile, clade, region, weighted_avg_year):

            # first calculate weighted average
            # total = 0
            # total_weights = 0
            # for aminoAcid in profile:
            #     if abs(profile[aminoAcid]) == float('inf'):  # skip inf
            #         continue
            #     weight = self.fits[(clade, region)][aminoAcid].r
            #     total_weights += weight
            #     total += profile[aminoAcid] * weight
            # weighted_avg = total / total_weights

            # usage weighted best matching year for average
            weighted_avg = weighted_avg_year

            # then calculate weighted stdev
            weighted_square_sum = 0
            for aminoAcid in profile:
                if abs(profile[aminoAcid]) == float('inf'):  # skip inf
                    continue
                r2 = self.fits[(clade, region)][aminoAcid].r
                avg_percentage = calc_avg_percentage(aminoAcid, clade, region)
                percent = self.input.profile[aminoAcid]
                weight = r2 * ((percent + avg_percentage) / 2) ** .5
                weighted_square_sum += weight * (profile[aminoAcid] - weighted_avg) ** 2
            return (weighted_square_sum / (len(profile) - 1)) ** .5

        def calc_stdev(profile):
            sum = 0
            for aminoAcid in profile:
                sum += profile[aminoAcid]
            mean = sum / len(profile)
            sum = 0
            for aminoAcid in profile:
                sum += (profile[aminoAcid] - mean) ** 2
            return (sum / (len(profile) - 1)) ** .5

        def calc_best_matching_year(profile, clade, region):

            # weighted sum and number of year entries
            weighted_year_sum = 0
            weighted_year_num = 0
            for aminoAcid in profile:
                if abs(profile[aminoAcid]) == float('inf'):  # skip inf
                    continue
                r2 = self.fits[(clade, region)][aminoAcid].r
                avg_percentage_profile = calc_avg_percentage(aminoAcid, clade, region)
                percent = self.input.profile[aminoAcid]
                weight = r2 * ((percent + avg_percentage_profile) / 2) ** .5
                weighted_year_sum += weight * profile[aminoAcid]
                weighted_year_num += weight

            return weighted_year_sum / weighted_year_num

        score = sys.float_info.max
        for clade, region in self.results:
            profileDict = self.results[(clade, region)]
            # cur_score = calc_stdev(profileDict)
            cur_best_match_year = calc_best_matching_year(profileDict, clade, region)
            cur_score = clac_r2_weighted_stdev(profileDict, clade, region, cur_best_match_year)
            self.scores[(clade, region)] = cur_score
            self.best_match_years[(clade, region)] = cur_best_match_year
            if cur_score < score:
                score = cur_score
                self.best_fit_clade = clade
                self.best_fit_region = region
        return self.best_fit_clade, self.best_fit_region

    # write intermediate results for verfication purposes
    def write_intermediate_results(self, fileName):
        all_rows = []
        amino_acids_list = []
        for aminoAcid in constants.AminoAcid:
            amino_acids_list.append(aminoAcid.value)

        # query rows
        all_rows.append(['position:', str(self.input.position)])
        all_rows.append(['clade:', self.input.clade.value])
        all_rows.append(['region:', self.input.region.value])
        all_rows.append(['period', self.input.year_range])
        all_rows.append(['', '', '', ''] + amino_acids_list)
        query_row = ['query', '', '','']
        for aminoAcid in constants.AminoAcid:
            query_row.append(self.input.profile[aminoAcid])
        all_rows.append(query_row)
        all_rows.append([])

        # calculated year, stdev, and fit parameters
        all_rows.append(['', 'stdev', 'best match year', ''] + amino_acids_list)
        print(len(self.results))
        for clade, region in self.results:
            row_collection = [
                [clade.value + ", " + region.value, self.scores[clade, region], self.best_match_years[clade, region], ''],
                ['slope', '', '', ''],
                ['y_intercept', '', '', ''],
                ['r', '', '',''],
                []
            ]
            for aminoAcid in constants.AminoAcid:
                row_collection[0].append(self.results[(clade, region)][aminoAcid])
                row_collection[1].append(self.fits[(clade, region)][aminoAcid].slope)
                row_collection[2].append(self.fits[(clade, region)][aminoAcid].y_intercept)
                row_collection[3].append(self.fits[(clade, region)][aminoAcid].r)
            for row in row_collection:
                all_rows.append(row)
            all_rows.append([])

        # write all other profiles that shared the same period with query
        period = calcYear(self.input.year_range)
        all_other_profiles = {}  # {(clade, region) -> {AminoAcid -> percentage}}
        # for profile in self.all_profiles.profiles:
        all_profiles = get_all_dynamic_profiles()
        all_profiles = all_profiles.filter(position=self.input.position)
        for profile in all_profiles.get_all_profiles():
            key = profile.clade(), profile.region()
            amino_acid = profile.amino_acid()
            percentage = None
            for i in range(0, len(profile.years)):
                if profile.years[i] == period:
                    percentage = profile.distr[i]
                    break
            try:
                all_other_profiles[key][amino_acid] = percentage
            except KeyError:
                all_other_profiles[key] = {amino_acid: percentage}

        # put all other profiles into the list of rows to be writteqn
        all_rows.append([])
        all_rows.append(['other profiles in the same period'])
        all_rows.append(['', '', ''] + amino_acids_list)
        for clade, region in all_other_profiles:
            profile = all_other_profiles[(clade, region)]
            percentage_row = [clade.value + ", " + region.value, '']
            for amino_acid in constants.AminoAcid:
                percentage_row.append(profile[amino_acid])
            all_rows.append(percentage_row)

        # write to output file
        with open(fileName, 'w') as outFile:
            writer = csv.writer(outFile, lineterminator='\n')
            writer.writerows(all_rows)


if __name__ == '__main__':

    query_inputs = [
        QueryInput(constants.query_profile_B_NA_295_05_to_09, 295, '[2005, 2009]', constants.Clade.B, constants.Region.NA),
        QueryInput(constants.query_profile_B_NA_332_05_to_09, 332, '[2005, 2009]', constants.Clade.B, constants.Region.NA),
        QueryInput(constants.query_profile_B_NA_339_05_to_09, 339, '[2005, 2009]', constants.Clade.B, constants.Region.NA),
        QueryInput(constants.query_profile_B_NA_392_05_to_09, 392, '[2005, 2009]', constants.Clade.B, constants.Region.NA),
        QueryInput(constants.query_profile_B_NA_448_05_to_09, 448, '[2005, 2009]', constants.Clade.B, constants.Region.NA)
    ]

    for query_input in query_inputs:
        allProfiles = get_all_dynamic_profiles()
        for p in allProfiles.get_all_profiles():
            calcFit(p)
        query = Query(query_input, allProfiles)
        print(query.best_fit_clade)
        print(query.best_fit_region)
        file_name = join(sys.argv[1], str(query_input.position) + '_r2=0.4.csv')
        query.write_intermediate_results(file_name)
