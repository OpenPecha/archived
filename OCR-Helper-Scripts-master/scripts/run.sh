# run OCR
rm -rf output/

nohup python3 img2opf/usage/bdrc/bdrc_ocr.py --input_path=./input/input1 &
nohup python3 img2opf/usage/bdrc/bdrc_ocr.py --input_path=./input/input2 &
nohup python3 img2opf/usage/bdrc/bdrc_ocr.py --input_path=./input/input3 &
nohup python3 img2opf/usage/bdrc/bdrc_ocr.py --input_path=./input/input4 &

# cmd
# ( nohup sh run.sh 2>&1 | ts '[%Y-%m-%d %H:%M:%S]' ) >> nohup.log &
