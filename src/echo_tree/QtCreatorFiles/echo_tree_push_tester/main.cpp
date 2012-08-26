#include <QtGui/QApplication>
#include "wordpushergui.h"

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    WordPusherGui w;
    w.show();

    return a.exec();
}
