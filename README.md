TODO:
better exception handling,
make a class PlantController and restructure code accordingly,

INSTALLATION NOTES:
for water temp sensor ds18b20, we must add a line to the boot config

/boot/config.txt
dtoverlay=w1-gpio,gpiopin=x

x can be any pin, but we used 27.

