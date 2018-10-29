import unittest
import constants
import convergence_p_value


class TestProfilePValue(unittest.TestCase):

    def test_envlopes_to_profile(self):
        sequences = \
            ['Z'] * 10 + \
            ['N'] * 50 + \
            ['T'] * 1
        prof = convergence_p_value.envelopes_to_profile(sequences, 0)
        for aa in constants.AminoAcid:
            if aa == constants.AminoAcid.Z:
                self.assertAlmostEqual(0.21467016498, prof[aa])
            elif aa == constants.AminoAcid.N:
                self.assertAlmostEqual(0.91364016932, prof[aa])
            else:
                self.assertEqual(0, prof[aa])