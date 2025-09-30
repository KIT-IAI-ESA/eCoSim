#!/bin/bash

source /integration_test/config.sh

FAILED=$(ls "$IT_RESULTS"/fail* 2>/dev/null)

if [ -z "$FAILED" ]; then
    echo "All tests passed."
    echo "SUCCESS" > "$FINAL_RESULT"
    exit 0
fi

echo "FAIL" > "$FINAL_RESULT"
echo "Some tests failed."
echo ""
echo "Printing failed tests:"
for FILE in $FAILED; do
    echo "---- $FILE ----"
    cat "$FILE"
    echo "-------------------------"
done
exit 123
