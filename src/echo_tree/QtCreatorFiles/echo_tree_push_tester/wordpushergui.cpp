#include "wordpushergui.h"
#include "ui_wordpushergui.h"

WordPusherGui::WordPusherGui(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::WordPusherGui)
{
    ui->setupUi(this);
}

WordPusherGui::~WordPusherGui()
{
    delete ui;
}
