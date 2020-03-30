### Description
Scrapers for following newspapers:  
    1. [Politika](http://www.politika.rs)  
    2. [Kurir](https://www.kurir.rs/)  
    3. [Srbija danas](https://www.srbijadanas.com/)  
    4. [Alo](http://alo.rs/)  
    5. [Delo](https://www.delo.si/)  
    6. [Dnevnik](dnevnik.si)  
    7. [Slovenske novice](https://www.slovenskenovice.si/)  
    8. [Večer](https://www.vecer.com/)  
    9. [Svet24](http://svet24.si/)  
    10. [24ur](https://www.24ur.com/)  

Obtained articles are the result of a search using keywords defined in [constants.py](constants.py), within a range defined with **MIN_DATE** and **MAX_DATE** in the same file. 

Articles for each newspaper can be found in *:newspaper:/data/article* folder.

### Instructions
Code is written in ***Python 3.7***.

1. Create new [Conda](https://www.anaconda.com/) environment by running following command from root of the project:
`
conda create --name <env> --file requirements.txt
`
2. Run `python main.py`
