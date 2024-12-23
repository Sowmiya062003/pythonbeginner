# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press Ctrl+F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')
numbers=[1,2,4,5,6,7]
sum=0
for num in range(len(numbers)):
 sum+=numbers[num]
print(sum)
"""for i in range(3):
        for j in range(2):
            print(f"i={i}, j={j}")"""
'''for i in range(10):
        if i % 2 == 0:  # Skip even numbers
            continue
        print(i)'''
'''n=bool(input("Enter any Response"))
print(type(n))
n=int(input("Enter Age : "))
if (n>=18):
    print("Adult")
elif(n>=12) and (n<=17):
    print("teenager")
else:
    print("kid")'''

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
"""def greet(name1) :
    print(f"Hi,{name1}. Guten Morgen")
def food(Food) :
    print(f"I love {Food} too!, That's great")
n=input("Enter a name to print")
f=input("Enter your favourite food")
greet(n)
food(f)
print(type(n))"""

