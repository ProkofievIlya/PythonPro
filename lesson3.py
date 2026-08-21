# 1. Рядки
def string_length(text):
    length = len(text)
    return length


def concat_strings(text1, text2):
    result = text1 + text2
    return result


# 2. Числа
def square(number):
    result = number * number
    return result


def add_numbers(a, b):
    result = a + b
    return result


def divide_int(a, b):
    whole = a // b
    remainder = a % b
    return whole, remainder


# 3. Списки
def average(numbers):
    total = 0
    count = len(numbers)
    for i in range(count):
        total = total + numbers[i]
    avg = total / count
    return avg


def common_elements(list1, list2):
    result = []
    for i in range(len(list1)):
        item = list1[i]
        if item in list2:
            if item not in result:
                result.append(item)
    return result


# 4. Словники
def print_keys(dictionary):
    for key in dictionary:
        print(key)


def merge_dicts(dict1, dict2):
    new_dict = {}
    for key in dict1:
        new_dict[key] = dict1[key]
    for key in dict2:
        new_dict[key] = dict2[key]
    return new_dict


# 5. Множини
def union_sets(set1, set2):
    result = set1.union(set2)
    return result


def is_subset(set1, set2):
    if set1.issubset(set2):
        return True
    else:
        return False


# 6. Умовні вирази та цикли
def even_or_odd(number):
    if number % 2 == 0:
        print("Парне")
    else:
        print("Непарне")


def even_numbers(numbers):
    result = []
    for i in range(len(numbers)):
        if numbers[i] % 2 == 0:
            result.append(numbers[i])
    return result


# 7. Лямбда
check_even = lambda n: "парне" if n % 2 == 0 else "не парне"


print("----- 1. Рядки -----")
print(string_length("Привіт"))
print(concat_strings("Hello, ", "world!"))

print("----- 2. Числа -----")
print(square(5))
print(square(2.5))
print(add_numbers(3, 7))
print(add_numbers(1.5, 2.5))
whole, remainder = divide_int(17, 5)
print("ціла частина:", whole)
print("залишок:", remainder)

print("----- 3. Списки -----")
nums = [10, 20, 30, 40]
print(average(nums))
print(common_elements([1, 2, 3, 4, 2], [2, 4, 6, 8]))

print("----- 4. Словники -----")
d1 = {"ім'я": "Іван", "вік": 20, "група": "КН-21"}
print("ключі:")
print_keys(d1)
d2 = {"вік": 21, "місто": "Київ"}
print(merge_dicts(d1, d2))

print("----- 5. Множини -----")
s1 = {1, 2, 3}
s2 = {3, 4, 5}
print(union_sets(s1, s2))
print(is_subset({1, 2}, {1, 2, 3, 4}))
print(is_subset({1, 5}, {1, 2, 3}))

print("----- 6. Умови і цикли -----")
even_or_odd(8)
even_or_odd(7)
print(even_numbers([1, 2, 3, 4, 5, 6, 7, 8]))

print("----- 7. Лямбда -----")
print(check_even(10))
print(check_even(3))
