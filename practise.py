
if __name__ == '__main__':
#triangle pattern program
    """for j in range(1,5+1):
        print("*" * j)"""
#function program
"""def add_num(a,b):
    return a+b
n1=int(input("Enter number 1 :"))
n2=int(input("Enter number 2 :"))
res=add_num(n1,n2)
print(f"The addition of 2 number is {res}")"""

#variable inside a function
"""def variable_declaration():
    x=10
    print(f"the value of X is {x}")
variable_declaration()"""
# function for finding oddoreven

"""def is_oddoreven(num):
    if num%2==0:
        return True
num=int(input("enter number to check :"))
if (is_oddoreven(num) is True):
    print(f"{num} is even")
else:
    print(f"{num} is odd")
"""

#try except method (Error handling)
"""
try:
    num = int(input("Enter a number: "))
    result = 10 / num
    print(f"Result: {result}")
except ZeroDivisionError:
    print("Error: You cannot divide by zero!")
except ValueError:
    print("Error: Please enter a valid number!")
"""
#try except with finally
try:
    file=open("text.txt","r")
    cont=file.read()
    print(cont)
except FileNotFoundError:
    print("File not found")
finally:
    print("Trail successful")


