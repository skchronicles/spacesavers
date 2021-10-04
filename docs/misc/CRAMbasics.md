## CRAM file format (lossless only)

* It is uses reference based compression. This means that Samtools needs the reference genome sequence in order to decode a CRAM file.
* Alignments should be kept in chromosome/position sort order., i.e., CRAM is always coordinate sorted.
* The reference must be available at all times. Losing it may be equivalent to losing all your read sequences.
* The reference sequence is linked to by the md5sum (M5 auxiliary tag) in the CRAM header (@SQ tags). This is mandatory and part of the CRAM specification.
* In SAM/BAM format, these M5 tags are optional. Therefore converting from SAM/BAM to CRAM requires some additional overhead to link the CRAM to the correct reference sequence.

### SAM/BAM to CRAM conversion

```bash
% samtools view -T ref.fasta -C -o test.cram test.bam
```

Things to note about `-T` option:

* the `ref.fasta` file needs to be FASTA format and can optionally compressed by **bgzip**.
* it should be indexed by **samtools** **faidx**. If an index is not present one will be generated if the reference file is local.
* it can be "not-local" and be a https://, s3:// or other URL.
  * If it is "not-local" then the faidx file should also ideally be at the same location

If the BAM file already has M5 and UR tags then the `-T` can be dropped.

```bash
% samtools view -C -o test.cram test.bam
```

**How to add M5 and UR tags to bam file??**: One solution is to use Bamutil on biowulf:

```bash
% bam polishBAM --fasta ref.fa --in test.bam --out test.polished.bam
```

Here, `test.polished.bam` is supposed to have M5 and UR tags ... but this failed in testing. In testing, test.bam and test.polished.bam seem to be identical.... Weird!

### Viewing CRAM files or converting them to SAM/BAM

Again, the reference is required. The UR tag in CRAM file has the location of each reference sequence. Each sequences MD5Sum is also saved as a M5 tag in the @SQ header line. If the original sequence has moved or has been renamed then retrieval is almost impossible. Two possible solutions to this:

* save the reference sequences in a immutable s3 bucket (add and forget)

* create a local cache of reference sequences. This can be done as follows:

  * use the `seq_cache_populate.pl` script bundled with samtools

    ```bash
    % seq_cache_populate.pl --root /path/to/common/folder ref.fasta
    ```

  * Export the location of this common folder via REF_CACHE env variable

    ```bash
    % export REF_CACHE=/path/to/common/folder/%2s/%2s/%s
    ```

Off course, if you know the location of the reference then,

```bash
% samtools view -b -T /path/to/ref.fasta -o test.bam -@8 test.cram
```

### Some testing

* bam to cram

```bash
% samtools view -T ../../resources/mm10/other/mm10.plus_rDNA_plus_5S.id90_masked.rRNA_pseudogenes_masked.fa -C -o WT3_resent.minus.toSNPcalling.cram WT3_resent.minus.toSNPcalling.bam
```

size difference

```bash
 % ls -arlth WT3_resent.minus.toSNPcalling.*am
-rw-rw-r-- 1 kopardevn RBL_NCI 88M Sep  7 15:14 WT3_resent.minus.toSNPcalling.bam
-rw-rw-r-- 1 kopardevn RBL_NCI 27M Sep 15 21:35 WT3_resent.minus.toSNPcalling.cram
```

* bam to cram to bam

```bash
% samtools view -C -o WT3_resent.minus.toSNPcalling.cram2bam2cram.cram WT3_resent.minus.toSNPcalling.cram2bam.bam
```

size differences

```bash
 % ls -arlth WT3_resent.minus.toSNPcalling.*am
-rw-rw-r-- 1 kopardevn RBL_NCI 88M Sep  7 15:14 WT3_resent.minus.toSNPcalling.bam
-rw-rw-r-- 1 kopardevn RBL_NCI 27M Sep 15 21:35 WT3_resent.minus.toSNPcalling.cram
-rw-rw-r-- 1 kopardevn RBL_NCI 92M Sep 15 21:39 WT3_resent.minus.toSNPcalling.cram2bam.bam
```

header differences

```bash
% for f in WT3_resent.minus.toSNPcalling.bam WT3_resent.minus.toSNPcalling.cram WT3_resent.minus.toSNPcalling.cram2bam.bam;do echo $f;samtools view -H $f|head -n5;done
WT3_resent.minus.toSNPcalling.bam
@HD	VN:1.5	SO:coordinate
@SQ	SN:chr1	LN:195471971
@SQ	SN:chr2	LN:182113224
@SQ	SN:chr3	LN:160039680
@SQ	SN:chr4	LN:156508116
WT3_resent.minus.toSNPcalling.cram
@HD	VN:1.5	SO:coordinate
@SQ	SN:chr1	LN:195471971	M5:155e60353e04620c1ae2a4273b5c980e	UR:/gpfs/gsfs11/users/RBL_NCI/Wolin/mESC_slam_analysis/find_mutation_090721/star/../../resources/mm10/other/mm10.plus_rDNA_plus_5S.id90_masked.rRNA_pseudogenes_masked.fa
@SQ	SN:chr2	LN:182113224	M5:01ad8fdc245bd146c69dbeb97d9adeb2	UR:/gpfs/gsfs11/users/RBL_NCI/Wolin/mESC_slam_analysis/find_mutation_090721/star/../../resources/mm10/other/mm10.plus_rDNA_plus_5S.id90_masked.rRNA_pseudogenes_masked.fa
@SQ	SN:chr3	LN:160039680	M5:91ada520bad86f25781017213b7e007f	UR:/gpfs/gsfs11/users/RBL_NCI/Wolin/mESC_slam_analysis/find_mutation_090721/star/../../resources/mm10/other/mm10.plus_rDNA_plus_5S.id90_masked.rRNA_pseudogenes_masked.fa
@SQ	SN:chr4	LN:156508116	M5:5a280a14bfb9a64ba8f3e80e5e3b5b90	UR:/gpfs/gsfs11/users/RBL_NCI/Wolin/mESC_slam_analysis/find_mutation_090721/star/../../resources/mm10/other/mm10.plus_rDNA_plus_5S.id90_masked.rRNA_pseudogenes_masked.fa
WT3_resent.minus.toSNPcalling.cram2bam.bam
@HD	VN:1.5	SO:coordinate
@SQ	SN:chr1	LN:195471971	M5:155e60353e04620c1ae2a4273b5c980e	UR:/gpfs/gsfs11/users/RBL_NCI/Wolin/mESC_slam_analysis/find_mutation_090721/star/../../resources/mm10/other/mm10.plus_rDNA_plus_5S.id90_masked.rRNA_pseudogenes_masked.fa
@SQ	SN:chr2	LN:182113224	M5:01ad8fdc245bd146c69dbeb97d9adeb2	UR:/gpfs/gsfs11/users/RBL_NCI/Wolin/mESC_slam_analysis/find_mutation_090721/star/../../resources/mm10/other/mm10.plus_rDNA_plus_5S.id90_masked.rRNA_pseudogenes_masked.fa
@SQ	SN:chr3	LN:160039680	M5:91ada520bad86f25781017213b7e007f	UR:/gpfs/gsfs11/users/RBL_NCI/Wolin/mESC_slam_analysis/find_mutation_090721/star/../../resources/mm10/other/mm10.plus_rDNA_plus_5S.id90_masked.rRNA_pseudogenes_masked.fa
@SQ	SN:chr4	LN:156508116	M5:5a280a14bfb9a64ba8f3e80e5e3b5b90	UR:/gpfs/gsfs11/users/RBL_NCI/Wolin/mESC_slam_analysis/find_mutation_090721/star/../../resources/mm10/other/mm10.plus_rDNA_plus_5S.id90_masked.rRNA_pseudogenes_masked.fa
```

CRAM file has the M5 and UR tags in @SQ header lines. BAM created from CRAM also has these tags. (such BAMs can be directly converted to CRAM without the `-T` argument)

### Testing `seq_cache_populate.pl`

Using `test.fa` for testing:

```bash
% cat tmp.fa
>5S
GTCTACGGCCATACCACCCTGAACGCGCCCGATCTCGTCTGATCTCGGAAGCTAAGCAGGGTCGGGCCTGGTTAGTACTTGGATGGGAGACCGCCTGGGAATACCGGGTGCTGTAGGCTTTGGACTCCCCTCTGTCTCTCTCTCCCTTTT
```

Add it to REF_CACHE

```bash
% seq_cache_populate.pl --root /lscratch/$SLURM_JOBID/ref_path ./test.fa
Reading ./test.fa ...
/lscratch/23025678/ref_path/2a/c6/36dca37eb7a6f2f222c7b5ef5e96 5S

Use environment REF_CACHE=/lscratch/23025678/ref_path/%2s/%2s/%s for accessing these files.
See also https://www.htslib.org/workflow/#the-ref_path-and-ref_cache for
further information.
```

* Per line sequence width does not matter

  ```bash
  % module load fastxtoolkit
  % fasta_formatter -i test.fa -w 80 -o test.w80.fa
  % more test.w80.fa
  >5S
  GTCTACGGCCATACCACCCTGAACGCGCCCGATCTCGTCTGATCTCGGAAGCTAAGCAGGGTCGGGCCTGGTTAGTACTT
  GGATGGGAGACCGCCTGGGAATACCGGGTGCTGTAGGCTTTGGACTCCCCTCTGTCTCTCTCTCCCTTTT
   % seq_cache_populate.pl --root /lscratch/$SLURM_JOBID/ref_path ./test.w80.fa
  Reading ./test.w80.fa ...
  Already exists: 2ac636dca37eb7a6f2f222c7b5ef5e96 5S
  
  Use environment REF_CACHE=/lscratch/23025678/ref_path/%2s/%2s/%s for accessing these files.
  See also https://www.htslib.org/workflow/#the-ref_path-and-ref_cache for
  further information.
  ```

* Sequence description does not matter

  ```bash
  # adding description to sequence name
  % cat test.desc.fa
  >5S Some Description
  GTCTACGGCCATACCACCCTGAACGCGCCCGATCTCGTCTGATCTCGGAAGCTAAGCAGGGTCGGGCCTGGTTAGTACTTGGATGGGAGACCGCCTGGGAATACCGGGTGCTGTAGGCTTTGGACTCCCCTCTGTCTCTCTCTCCCTTTT
  % seq_cache_populate.pl --root /lscratch/$SLURM_JOBID/ref_path test.desc.fa
  Reading test.desc.fa ...
  Already exists: 2ac636dca37eb7a6f2f222c7b5ef5e96 5S
  
  Use environment REF_CACHE=/lscratch/23025678/ref_path/%2s/%2s/%s for accessing these files.
  See also https://www.htslib.org/workflow/#the-ref_path-and-ref_cache for
  further information.
  ```

* Changing sequence name (ID) does not matter

  ```bash
  % cat test.newid.fa
  >chr5S
  GTCTACGGCCATACCACCCTGAACGCGCCCGATCTCGTCTGATCTCGGAAGCTAAGCAGGGTCGGGCCTGGTTAGTACTTGGATGGGAGACCGCCTGGGAATACCGGGTGCTGTAGGCTTTGGACTCCCCTCTGTCTCTCTCTCCCTTTT
  % seq_cache_populate.pl --root /lscratch/$SLURM_JOBID/ref_path test.newid.fa
  Reading test.newid.fa ...
  Already exists: 2ac636dca37eb7a6f2f222c7b5ef5e96 chr5S
  
  Use environment REF_CACHE=/lscratch/23025678/ref_path/%2s/%2s/%s for accessing these files.
  See also https://www.htslib.org/workflow/#the-ref_path-and-ref_cache for
  further information.
  ```





