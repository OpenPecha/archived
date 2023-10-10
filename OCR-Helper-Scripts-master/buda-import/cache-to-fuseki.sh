for f in $(find ttl-cache -name '*.ttl.gz'); do 
	echo "$f"
	bn="$(basename $f .ttl.gz)"
	curl -X PUT -H 'Content-Type:text/turtle' -H 'Content-Encoding: gzip' -T "$f" -G 'http://buda4.bdrc.io:13180/fuseki/corerw/data' --data-urlencode "graph=http://purl.bdrc.io/graph/$bn"
done