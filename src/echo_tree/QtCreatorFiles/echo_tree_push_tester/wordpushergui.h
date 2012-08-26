#ifndef WORDPUSHERGUI_H
#define WORDPUSHERGUI_H

#include <QMainWindow>

namespace Ui {
    class WordPusherGui;
}

class WordPusherGui : public QMainWindow
{
    Q_OBJECT

public:
    explicit WordPusherGui(QWidget *parent = 0);
    ~WordPusherGui();

private:
    Ui::WordPusherGui *ui;
};

#endif // WORDPUSHERGUI_H
