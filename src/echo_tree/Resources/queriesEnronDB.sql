select word,follower,followingCount from EnronWords where word="my" order by followingCount*1 desc;
select word,follower,followingCount from EnronWords where word="reliability" order by followingCount*1 desc;
select word,follower,followingCount from EnronWords where word="speed" order by followingCount*1 desc;

select word from EnronWords where word="reliability";
select word from EnronWords where word="my";
select word,follower,followingCount from EnronWords where word="not";



select word,follower,followersCount from EnronWords where word="my" and follower"dad" order by followersCount*1 desc
select word,follower,followersCount from EnronWords where word="look";

select max(followersCount from
	(select word,follower,followersCount from EnronWords where word="look");