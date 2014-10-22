# ----------------------------------------------------------------------------
# Copyright (c) 2013--, scikit-bio development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

from __future__ import absolute_import, division, print_function

from unittest import TestCase, main
from six import StringIO
from skbio import (BiologicalSequence, NucleotideSequence, DNA, RNA, Protein)
from skbio import SequenceCollection, Alignment

from skbio.io import FASTQFormatError
from skbio.io.fastq import (
    _fastq_sniffer, _fastq_to_generator, _fastq_to_biological_sequence,
    _fastq_to_nucleotide_sequence, _fastq_to_dna_sequence,
    _fastq_to_rna_sequence, _fastq_to_protein_sequence,
    _fastq_to_sequence_collection, _fastq_to_alignment, _generator_to_fastq,
    ascii_to_phred33, ascii_to_phred64)

from skbio.util import get_data_path


class FASTQSnifferTests(TestCase):
    def setUp(self):
        self.positive_fps_33 = map(get_data_path, [
            'fastq_multi_seq33',
            'fastq_multi_seq33_without_header'
        ])

        self.positive_fps_64 = map(get_data_path, [
            'fastq_single_seq',
            'fastq_multi_seq',
            'fastq_multi_seq64',
            'fastq_single_nuc64',
            'fastq_single_rna64',
            'fastq_single_prot64'
        ])

        self.negative_fps = map(get_data_path, [
            'empty',
            'fastq_invalid_missing_header',
            'fastq_invalid_missing_qual_header',
        ])

    def test_positives(self):
        for fp in self.positive_fps_33:
            self.assertEqual(_fastq_sniffer(fp), (True, {'phred_offset': 33}))
        for fp in self.positive_fps_64:
            self.assertEqual(_fastq_sniffer(fp), (True, {'phred_offset': 64}))

    def test_negatives(self):
        for fp in self.negative_fps:
            self.assertEqual(_fastq_sniffer(fp), (False, {}))


class FASTQReaderTests(TestCase):
    def setUp(self):
        self.empty = ([], {}, map(get_data_path, ['empty']))
        self.single = (
            [BiologicalSequence('AACACCAAACTTCTCCACCACGTGAGCTACAAAAG',
                                id='seq1',
                                quality=ascii_to_phred64(
                                    '````Y^T]`]c^cabcacc`^Lb^ccYT\T\Y\WF'))],
            {'phred_offset': 64},
            map(get_data_path, ['fastq_single_seq'])
        )

        self.multi = (
            [BiologicalSequence('ACGTT', id='k',
                                description='ok',
                                quality=ascii_to_phred64(
                                    r'^\\\Y')),
             BiologicalSequence('AACGGuA', id='desc3',
                                quality=ascii_to_phred64(
                                    'bbbbbbb')),
             BiologicalSequence('AcGtUTu', id='seq1',
                                quality=ascii_to_phred64(
                                    'bbkqwbo')),
             BiologicalSequence('ACGTTGCAccGG',
                                quality=ascii_to_phred64(
                                    'BBBBBBBBBBBB')),
             BiologicalSequence('ACGUU',
                                quality=ascii_to_phred64(
                                    r'^\\\Y'))],
            {'phred_offset': 64},
            map(get_data_path, ['fastq_multi_seq'])
        )

        self.multi33 = (
            [BiologicalSequence('GTTGCTTCTGGCGTGGGTGGGGGGG',
                                id=r'EAS54_6_R1_2_1_443_348',
                                quality=ascii_to_phred33(
                                    r';;;;;;;;;;;9;7;;.7;393333')),
             BiologicalSequence('GATTTGGGGTTCAAAGCAGTATCGATCAAA'
                                'TAGTAAATCCATTTGTTCAACTCACAGTTT',
                                id=r'SEQ_ID',
                                quality=ascii_to_phred33(
                                    r"!''*((((***+))%%%++)(%%%%).1**"
                                    "*-+*''))**55CCF>>>>>>CCCCCCC65"))],
            {'phred_offset': 33},
            map(get_data_path, ['fastq_multi_seq33',
                                'fastq_multi_seq33_without_header']))

        self.multi64 = (
            [BiologicalSequence('AACACCAAACTTCTCCACCACGTGAGCTACAAAAG',
                                id=r'GAPC_0015:6:1:1259:10413#0/1',
                                quality=ascii_to_phred64(
                                    r'````Y^T]`]c^cabcacc`^Lb^ccYT\T\Y\WF')),
             BiologicalSequence('TATGTATATATAACATATACATATATACATACATA',
                                id=r'GAPC_0015:6:1:1283:11957#0/1',
                                quality=ascii_to_phred64(
                                    r']KZ[PY]_[YY^```ac^\\`bT``c`\aT``bbb')),
             BiologicalSequence('TCAGTTTTCCTCGCCATATTTCACGTCCTAAAGCG',
                                id=r'GAPC_0015:6:1:1284:10484#0/1',
                                quality=ascii_to_phred64(
                                    r'UM_]]U_]Z_Y^\^^``Y]`^SZ]\Ybb`^_LbL_')),
             BiologicalSequence('TGTGCCTATGGAAGCAGTTCTAGGATCCCCTAGAA',
                                id=r'GAPC_0015:6:1:1287:17135#0/1',
                                quality=ascii_to_phred64(
                                    r'^aacccL\ccc\c\cTKTS]KZ\]]I\[Wa^T`^K')),
             BiologicalSequence('AAAGAAAGGAAGAAAAGAAAAAGAAACCCGAGTTA',
                                id=r'GAPC_0015:6:1:1293:3171#0/1',
                                quality=ascii_to_phred64(
                                    r'b`bbbU_[YYcadcda_LbaaabWbaacYcc`a^c')),
             BiologicalSequence('TAATGCCAAAGAAATATTTCCAAACTACATGCTTA',
                                id=r'GAPC_0015:6:1:1297:10729#0/1',
                                quality=ascii_to_phred64(
                                    r'T\ccLbb``bacc]_cacccccLccc\ccTccYL^'))],
            {'phred_offset': 64},
            map(get_data_path, ['fastq_multi_seq64']))

        self.invalid_fps = map(lambda e: (get_data_path(e[0]), e[1]), [
            ('fastq_invalid_bad_id', 'ID mismatch'),
            ('fastq_invalid_missing_header', 'Bad FASTQ format'),
            ('fastq_invalid_bad_qual', 'Failed qual conversion')
        ])

        self.invalid = []

        # sequences that can be loaded into a SequenceCollection or Alignment.
        # they are also a different type than BiologicalSequence in order to
        # exercise the constructor parameter
        self.sequence_collection_different_type = (
            [RNA('AUG', quality=ascii_to_phred64('bbb')),
             RNA('AUC', id='rnaseq-1', description='rnaseq desc 1',
                 quality=ascii_to_phred64('bbb')),
             RNA('AUG', id='rnaseq-2', description='rnaseq desc 2',
                 quality=ascii_to_phred64('bbb'))],
            {'constructor': RNA, 'phred_offset': 64},
            map(get_data_path, ['fastq_sequence_collection_different_type'])
        )

    def test_fastq_to_generator_valid_files(self):

        for exp, kwargs, fps in (self.multi, self.empty, self.single,
                                 self.multi33, self.multi64,
                                 self.sequence_collection_different_type):
            for fp in fps:
                obs = list(_fastq_to_generator(fp, **kwargs))

                self.assertEqual(len(obs), len(exp))
                for o, e in zip(obs, exp):
                    if not o.equals(e):
                        print(o)
                        print(e)
                    self.assertTrue(o.equals(e))

    def test_fastq_to_generator_invalid_files(self):
        for fp, error_msg_regex in self.invalid_fps:
            with self.assertRaisesRegexp(FASTQFormatError, error_msg_regex):
                list(_fastq_to_generator(fp, strict=True))

    def test_fastq_to_any_sequence(self):
        for constructor, reader_fn in ((BiologicalSequence,
                                        _fastq_to_biological_sequence),
                                       (NucleotideSequence,
                                        _fastq_to_nucleotide_sequence),
                                       (DNA,
                                        _fastq_to_dna_sequence),
                                       (RNA,
                                        _fastq_to_rna_sequence),
                                       (Protein,
                                        _fastq_to_protein_sequence)):

            # empty file
            with self.assertRaisesRegexp(FASTQFormatError, '1st biological'):
                reader_fn(get_data_path('empty'))

            # the sequences in the following files don't necessarily make sense
            # for each of the sequence object types that they're read into
            # (e.g., reading a protein sequence into a dna sequence object).
            # however, for the purposes of testing the various
            # fasta -> sequence readers, this works out okay as it is valid to
            # construct a sequence object with invalid characters. we're
            # interested in testing the reading logic here, and don't care so
            # much about constructing semantically-meaningful/valid sequence
            # objects

            # file with only 1 seq, get first
            for fp in map(get_data_path,
                          ['fastq_single_seq']):

                exp = constructor('AACACCAAACTTCTCCACCACGTGAGCTACAAAAG',
                                  id='seq1',
                                  quality=ascii_to_phred64(
                                      r'````Y^T]`]c^cabcacc`^Lb^ccYT\T\Y\WF'))
                obs = reader_fn(fp, phred_offset=64)
                self.assertTrue(obs.equals(exp))

            # file with multiple seqs
            for fp in map(get_data_path,
                          ['fastq_multi_diff_seq64']):
                # get first
                exp = constructor('ACGTacgt', id='seq1',
                                  description='desc1',
                                  quality=ascii_to_phred64('YYYYYYYY'))
                obs = reader_fn(fp, phred_offset=64)
                self.assertTrue(obs.equals(exp))

                # get middle
                exp = constructor('AcGtUTu',
                                  quality=ascii_to_phred64('bbbbbbb'))
                obs = reader_fn(fp, seq_num=2, phred_offset=64)
                self.assertTrue(obs.equals(exp))

                # get last
                exp = constructor(
                    'pQqqqPPQQQ', id='proteinseq',
                    quality=ascii_to_phred64('zzzzzzzzzz'),
                    description='detailed description with new lines')
                obs = reader_fn(fp, seq_num=3, phred_offset=64)
                self.assertTrue(obs.equals(exp))

    def test_fastq_to_sequence_collection_and_alignment(self):
        for constructor, reader_fn in ((SequenceCollection,
                                        _fastq_to_sequence_collection),
                                       (Alignment,
                                        _fastq_to_alignment)):
            for exp_list, kwargs, fps in \
                    (self.empty, self.single,
                     self.sequence_collection_different_type):
                exp = constructor(exp_list)

                for fp in fps:
                    obs = reader_fn(fp, **kwargs)

                    # TODO remove this custom equality testing code when
                    # SequenceCollection has an equals method (part of #656).
                    # We need this method to include IDs and description in the
                    # comparison (not part of SequenceCollection.__eq__).
                    self.assertEqual(obs, exp)
                    for o, e in zip(obs, exp):
                        self.assertTrue(o.equals(e))


class FASTQWriterTests(TestCase):
    def setUp(self):
        self.empty = ([], {}, map(get_data_path, ['empty']))
        self.multi33 = (
            [BiologicalSequence('GTTGCTTCTGGCGTGGGTGGGGGGG',
                                id=r'EAS54_6_R1_2_1_443_348',
                                quality=ascii_to_phred33(
                                    r';;;;;;;;;;;9;7;;.7;393333')),
             BiologicalSequence('GATTTGGGGTTCAAAGCAGTATCGATCAAA'
                                'TAGTAAATCCATTTGTTCAACTCACAGTTT',
                                id=r'SEQ_ID',
                                quality=ascii_to_phred33(
                                    r"!''*((((***+))%%%++)(%%%%).1**"
                                    "*-+*''))**55CCF>>>>>>CCCCCCC65"))],
            {'phred_offset': 33},
            map(get_data_path, ['fastq_multi_seq33']))
        self.multi64 = (
            [BiologicalSequence('AACACCAAACTTCTCCACCACGTGAGCTACAAAAG',
                                id=r'GAPC_0015:6:1:1259:10413#0/1',
                                quality=ascii_to_phred64(
                                    r'````Y^T]`]c^cabcacc`^Lb^ccYT\T\Y\WF')),
             BiologicalSequence('TATGTATATATAACATATACATATATACATACATA',
                                id=r'GAPC_0015:6:1:1283:11957#0/1',
                                quality=ascii_to_phred64(
                                    r']KZ[PY]_[YY^```ac^\\`bT``c`\aT``bbb')),
             BiologicalSequence('TCAGTTTTCCTCGCCATATTTCACGTCCTAAAGCG',
                                id=r'GAPC_0015:6:1:1284:10484#0/1',
                                quality=ascii_to_phred64(
                                    r'UM_]]U_]Z_Y^\^^``Y]`^SZ]\Ybb`^_LbL_')),
             BiologicalSequence('TGTGCCTATGGAAGCAGTTCTAGGATCCCCTAGAA',
                                id=r'GAPC_0015:6:1:1287:17135#0/1',
                                quality=ascii_to_phred64(
                                    r'^aacccL\ccc\c\cTKTS]KZ\]]I\[Wa^T`^K')),
             BiologicalSequence('AAAGAAAGGAAGAAAAGAAAAAGAAACCCGAGTTA',
                                id=r'GAPC_0015:6:1:1293:3171#0/1',
                                quality=ascii_to_phred64(
                                    r'b`bbbU_[YYcadcda_LbaaabWbaacYcc`a^c')),
             BiologicalSequence('TAATGCCAAAGAAATATTTCCAAACTACATGCTTA',
                                id=r'GAPC_0015:6:1:1297:10729#0/1',
                                quality=ascii_to_phred64(
                                    r'T\ccLbb``bacc]_cacccccLccc\ccTccYL^'))],
            {'phred_offset': 64},
            map(get_data_path, ['fastq_multi_seq64']))

        self.invalid_fps = map(lambda e: (get_data_path(e[0]), e[1]), [
            ('fastq_invalid_bad_id', 'ID mismatch'),
            ('fastq_invalid_missing_header', 'Bad FASTQ format'),
            ('fastq_invalid_bad_qual', 'Failed qual conversion')
        ])

    def test_generator_to_fastq(self):
        for obj, kwargs, fps in (self.empty, self.multi33, self.multi64):
            for fp in fps:
                fh = StringIO()
                _generator_to_fastq(obj, fh, **kwargs)
                obs = fh.getvalue()
                fh.close()

                with open(fp, 'U') as fh:
                    exp = fh.read()

            self.assertEqual(obs, exp)

    def test_fastq_to_generator_invalid_files(self):
        for fp, error_msg_regex in self.invalid_fps:
            with self.assertRaisesRegexp(FASTQFormatError, error_msg_regex):
                list(_fastq_to_generator(fp, strict=True))

if __name__ == '__main__':
    main()