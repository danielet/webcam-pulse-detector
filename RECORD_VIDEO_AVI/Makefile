CC=g++
PKG_CONFIG ?= `pkg-config opencv --cflags --libs`

# g++ `pkg-config opencv --cflags --libs` recordVideo.cpp -o image-conversion


all:
	$(CC) $(PKG_CONFIG) recordVideo.cpp -o recordVideo.out


.PHONY: clean

clean:
	rm -f ./*.out *~ 
	