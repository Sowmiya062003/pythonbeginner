
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
def is_oddoreven(num):
    if num%2==0:
        return True
num=int(input("enter number to check :"))
if (is_oddoreven(num) is True):
    print(f"{num} is even")
else:
    print(f"{num} is odd")
