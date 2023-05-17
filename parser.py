from bs4 import BeautifulSoup
import requests
import cookies, config
def main():
    URL = config.URL
    LOGIN_URL = config.LOGIN_URL
    auth_data = {"LoginForm[username]":config.email, "LoginForm[password]":config.password}
    cookie = {"Cookie":"PHPSESSIDBACK=" + cookies.PHPSESSIDBACK}
    with requests.session() as s:
        r = s.get(URL, headers=cookie)
    if "Завдання" in r.text:
        pass
    elif "Завдання" not in r.text:
        with requests.session() as s:
            s.get(LOGIN_URL, data = auth_data)
            r = s.get(URL)
            c = s.cookies.get('PHPSESSIDBACK')
            file = open('cookies.py', mode='w')
            file.write("PHPSESSIDBACK = '" + c + "'")
            file.close()

    soup = BeautifulSoup(r.content, 'html.parser')
    i = soup.find("li", {"class": "active"}).get_text()
    if i == "Завдання":
        i = 0
    elif i != "Завдання":
        i = 1
    return i

if __name__ == "__main__":
    main()
