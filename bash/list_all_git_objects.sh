for i in `cat objects/pack/pack-0f3b11a2aa32aa33d2835c34b57bddd793e3f620.idx | git show-index | cut -d ' ' -f 2`; do C=$i; [ `git cat-file -t $C` == "commit" ] && git --no-pager log -1 $C; done
for i in `find . -type f`; do C=`echo $i | sed 's#[\./]##g'`; [ `git cat-file -t $C` == "commit" ] && git --no-pager log -1 $C; done 
