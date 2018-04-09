from hashlib import sha1


# 求一个字符串的hash值
def get_hash(str):
	sh = sha1()
	sh.update(str.encode('utf-8'))
	return sh.hexdigest()