BASE_DIR=/data/unified/WmAgentScripts/
HTML_DIR=/var/www/html/unified/

lock_name=`echo $BASH_SOURCE | cut -f 1 -d "."`.lock
source $BASE_DIR/cycle_common.sh $lock_name

## get the workflow in/out of the system
$BASE_DIR/cWrap.sh Unified/injector.py

## get the batches of relval annnounced to HN
$BASE_DIR/cWrap.sh Unified/batchor.py

## this could replace stagor in much faster
## needs to put some work in stagor or not ?
$BASE_DIR/cWrap.sh Unified/assignor.py --early --limit 50

## get the workflow in/out the system
$BASE_DIR/cWrap.sh Unified/injector.py

## assigned those that could have passed through directly
$BASE_DIR/cWrap.sh Unified/assignor.py --from_status staged --limit 50

$BASE_DIR/cWrap.sh Unified/assignor.py _PR_newco --limit 50
$BASE_DIR/cWrap.sh Unified/assignor.py _PR_ref --limit 50

## assign the workflow to sites
$BASE_DIR/cWrap.sh Unified/assignor.py --limit 50

rm -f $lock_name

