#include "opencv2/opencv.hpp"
#include <iostream>

using namespace std;
using namespace cv;

int main(int argc, char ** argv){

    VideoCapture vcap(0); 
      if(!vcap.isOpened()){
             cout << "Error opening video stream or file" << endl;
             return -1;
      }

   int frame_width=   vcap.get(CV_CAP_PROP_FRAME_WIDTH);
   int frame_height=   vcap.get(CV_CAP_PROP_FRAME_HEIGHT);

   //PASSARLO DA RIGA DI COMMANDO
   VideoWriter video(argv[1],CV_FOURCC('M','J','P','G'),10, Size(frame_width,frame_height),true);

   for(;;){

       Mat frame;
       vcap >> frame;
       
       imshow( "Frame", frame );
       char c = (char)waitKey(33);

       switch(c)
       {
        case 27:
          return 1;
        break;
        case 102:
          printf("%d\n" , c);
        break;
       }
      video.write(frame);
       // if( c == 27 ) break;
    }
  return 0;
}