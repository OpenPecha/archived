<h1 align="center">
  <br>
  <a href="https://openpecha.org"><img src="https://avatars.githubusercontent.com/u/82142807?s=400&u=19e108a15566f3a1449bafb03b8dd706a72aebcd&v=4" alt="OpenPecha" width="150"></a>
  <br>
</h1>

# Generic Edition Generator

## Owner(s)

- [@eroux](https://github.com/eroux)
- [@kaldan007](https://github.com/kaldan007)

## RFXs

Requests for work (RFWs) and requests for comments (RFCs) associated with this project:

- [RFX name](#)

## Table of contents

<p align="center">
  <a href="#project-description">Project description</a> •
  <a href="#who-this-project-is-for">Who this project is for</a> •
  <a href="#project-dependencies">Project dependencies</a> •
  <a href="#instructions-for-use">Instructions for use</a> •
  <a href="#contributing-guidelines">Contributing guidelines</a> •
  <a href="#additional-documentation">Additional documentation</a> •
  <a href="#need-help">How to get help</a> •
  <a href="#terms-of-use">Terms of use</a>
</p>
<hr>

## Project description

The Generic Edition Generator is a tool used to create a clean e-text version of a Tibetan work from multiple flawed sources.

Benefits include:

- Automatic proofreading of Tibetan e-texts
- Creating high-quality e-texts from low-quality sources
- Doesn't require a spell checker (which doesn't exist yet for Tibetan language)

The Generic Edition Generator uses a weighted majority algorithm that compares versions of the work syllable by syllable and chooses the most common character from among the versions in each position of the text. Since mistakes—whether made during the woodblock carving, hand copying, digital text inputting, or OCRing process—are unlikely to be the same in the majority of the versions, they are unlikely to outrank the correct characters in any given position of the text. The result is a new clean version called a "vulgate edition."

### Vulgates or vulgate editions

**vulgate** (noun) /ˈvəl-ˌgāt/ or /ˈvʌlɡeɪt/: *2. a commonly accepted text or reading.*

Medieval Latin *vulgata*, from Late Latin *vulgata editio*: edition in general circulation.

“Vulgate.” Merriam-Webster.com Dictionary, Merriam-Webster, https://www.merriam-webster.com/dictionary/vulgate. Accessed 23 Dec. 2022.

This less common sense of the term *vulgate* represents the objective of this project.

## Who this project is for

This project is intended for:

- Publishers who need clean copies of texts to publish books
- Developers who need clean data to help train AI models
- Anyone who needs to proofread a Tibetan text and has access to multiple versions, such as in the [BDRC library](https://library.bdrc.io).

## Project dependencies

Before you start, ensure you've installed:

- python >= 3.8
- [openpecha](https://github.com/OpenPecha/Toolkit)
- [pedurma](https://github.com/Esukhia/pedurma)
- antx
- [fast-diff-match-patch](https://pypi.org/project/fast-diff-match-patch/)

## Requirements 

To create a vulgate edition, you'll need:

- A reference pecha in the OPF format
- Several witness pechas in the OPF format (a witness is a version of a text)

> **Note** To convert files into the OPF format, use [OpenPecha Tools](https://github.com/OpenPecha/Toolkit). 
> 
> You can also convert scanned texts in the [BDRC library](https://library.bdrc.io) to the OPF format with the [OCR Pipeline](https://tools.openpecha.org/ocr/).
> 
> To test Generic Edition Generator, you can also the OPF files in the [text folder](https://github.com/OpenPecha/generic-edition-generator/tree/main/test/) of this repo.

## Instructions for use

### Configure the Generic Edition Generator

Assuming you've installed the software above and have OPF files:

1. Clone this repo.
1. Add witnesses in the OPF format into your cloned repo.
1. Open `get_generic_editon.py` in a code editor.
1. Update the paths to the actual witness folders in this code block:

```
def test_merger():
	op_output = OpenPechaFS("ITEST.opf")
	vulgatizer = VulgatizerOPTibOCR(op_output)
	vulgatizer.add_op_witness(OpenPechaFS("./test/opfs/I001/I001.opf"))
	vulgatizer.add_op_witness(OpenPechaFS("./test/opfs/I002/I002.opf"))
	vulgatizer.add_op_witness(OpenPechaFS("./test/opfs/I003/I003.opf"))
	vulgatizer.create_vulgate()
```

### Run the Generic Edition Generator

- Run `get_generic_editon.py`

The vulgate edition OPF will be saved in `./data/opfs/generic_editions`.

### Limitations

- No code to detect [transpositions](http://multiversiondocs.blogspot.com/2008/10/transpositions.html).

## Contributing guidelines

If you'd like to help out, check out our [contributing guidelines](/CONTRIBUTING.md).

## Additional documentation

How the Generic Edition Generator creates a generic edition

![generic_flowchart](https://user-images.githubusercontent.com/24893704/206728922-66a60951-2a1f-4e16-9692-b9720853782b.jpg)

Previous work:

### text alignment

- [text_alignment_tool](https://gitlab.com/sofer_mahir/text_alignment_tool)
- [CollateX](https://collatex.net/about/)
- [MEDITE](http://www-poleia.lip6.fr/~ganascia/Medite_Project)
- [Juxta](https://wiki.digitalclassicist.org/Juxta) ([sources](https://github.com/performant-software/juxta-service), uses [difflib](https://github.com/java-diff-utils/java-diff-utils))
- [hypercollate](https://github.com/HuygensING/hyper-collate)
- [helayo](https://github.com/chchch/sanskrit-alignment) ([paper](https://joss.theoj.org/papers/10.21105/joss.04022))
- [Versioning Machine](http://v-machine.org/)
- [nmergec](http://digitalvariants.blogspot.com/2014/05/merging-multi-version-texts-mark-2.html) ("en-merge-see")

### OCR merging

- [ocromore](https://github.com/UB-Mannheim/ocromore)
- This was also done by Oliver Hellwig apparently, research to be one

### See also

- [Sequence Alignment (Wikipedia)](https://en.wikipedia.org/wiki/Sequence_alignment)
- [MSA: Multiple Sequence Alignment (Wikipedia)](https://en.wikipedia.org/wiki/Multiple_sequence_alignment)
- [Smith–Waterman algorithm](https://en.wikipedia.org/wiki/Smith%E2%80%93Waterman_algorithm)
- [Needleman–Wunsch algorithm](https://en.wikipedia.org/wiki/Needleman%E2%80%93Wunsch_algorithm)
- [Spencer 2004](http://dx.doi.org/10.1007/s10579-004-8682-1): Spencer M., Howe and Christopher J., 2004. Collating Texts Using Progressive Multiple Alignment. Computers and the Humanities. 38/2004, 253–270.

## Need help?

- File an [issue](https://github.com/OpenPecha/generic-edition-generator/issues/new)
- Join our [Discord](https://discord.com/invite/7GFpPFSTeA) and ask us there
- Email us at openpecha[at]gmail.com

## Terms of use

The Generic Edition Generator is licensed under the [MIT License](/LICENSE.md).
